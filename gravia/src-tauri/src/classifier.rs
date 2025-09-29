use std::collections::VecDeque;
use chrono::{DateTime, Utc, Duration};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,          // "user" or "assistant"
    pub content: String,
    pub timestamp: DateTime<Utc>,
    pub triggered_screenshot: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextInfo {
    pub has_context: bool,
    pub context_type: Option<String>,
    pub recent_screenshot: bool,
    pub assistant_gave_instructions: bool,
    pub user_in_middle_of_task: bool,
    pub context_strength: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClassificationResult {
    pub needs_screenshot: bool,
    pub confidence: f32,
    pub screenshot_score: i32,
    pub no_screenshot_score: i32,
    pub reasoning: Vec<String>,
    pub context_info: ContextInfo,
    // base64 screenshot if captured
    pub screenshot_base64: Option<String>,
}

pub struct ContextualScreenshotClassifier {
    chat_history: VecDeque<ChatMessage>,
    max_history: usize,
}

impl ContextualScreenshotClassifier {
    pub fn new(max_history: usize) -> Self {
        Self {
            chat_history: VecDeque::new(),
            max_history,
        }
    }
    
    pub fn add_message(&mut self, message: ChatMessage) {
        self.chat_history.push_back(message);
        if self.chat_history.len() > self.max_history {
            self.chat_history.pop_front();
        }
    }
    
    pub fn classify_with_context(&self, query: &str) -> ClassificationResult {
        let query_lower = query.to_lowercase();
        let mut screenshot_score = self.get_base_screenshot_score(&query_lower);
        let mut no_screenshot_score = self.get_base_no_screenshot_score(&query_lower);
        let mut reasoning = Vec::new();
        let context_info = self.analyze_recent_context();
        let mut confidence: f32 = 0.7;
        if context_info.has_context {
            if self.is_contextual_followup(&query_lower) {
                screenshot_score += 3;
                confidence += 0.2;
                reasoning.push(format!(
                    "Contextual follow-up after {}",
                    context_info.context_type.as_ref().unwrap_or(&"unknown".to_string())
                ));
            }
            if context_info.assistant_gave_instructions {
                let ambiguous_words = ["this", "that", "it", "here", "there"];
                if ambiguous_words.iter().any(|&word| query_lower.contains(word)) {
                    screenshot_score += 2;
                    confidence += 0.15;
                    reasoning.push("Ambiguous reference with UI context".to_string());
                }
            }
            if context_info.user_in_middle_of_task {
                screenshot_score += 1;
                confidence += 0.1;
                reasoning.push("Continuation of ongoing task".to_string());
            }
        }
        let clear_general = ["explain", "what is", "how to", "definition", "history"];
        if clear_general.iter().any(|&phrase| query_lower.contains(phrase)) {
            no_screenshot_score += 2;
            reasoning.push("Clear general knowledge query".to_string());
        }
        let needs_screenshot = screenshot_score > no_screenshot_score;
        ClassificationResult {
            needs_screenshot,
            confidence: confidence.min(0.95),
            screenshot_score,
            no_screenshot_score,
            reasoning,
            context_info,
            screenshot_base64: None,
        }
    }
    
    fn analyze_recent_context(&self) -> ContextInfo {
        let cutoff_time = Utc::now() - Duration::minutes(10);
        let recent_messages: Vec<&ChatMessage> = self.chat_history
            .iter()
            .rev()
            .take(10)
            .filter(|msg| msg.timestamp > cutoff_time)
            .collect();
        let mut context_info = ContextInfo {
            has_context: false,
            context_type: None,
            recent_screenshot: false,
            assistant_gave_instructions: false,
            user_in_middle_of_task: false,
            context_strength: 0,
        };
        for msg in recent_messages {
            let msg_lower = msg.content.to_lowercase();
            if msg.role == "assistant" {
                let ui_patterns = [
                    "go to", "click", "select", "find the", "open the",
                    "settings", "menu", "button", "option", "panel"
                ];
                if ui_patterns.iter().any(|&pattern| msg_lower.contains(pattern)) {
                    context_info.has_context = true;
                    context_info.context_type = Some("ui_navigation".to_string());
                    context_info.assistant_gave_instructions = true;
                    context_info.context_strength += 2;
                }
                let error_patterns = ["error", "problem", "issue", "troubleshoot"];
                if error_patterns.iter().any(|&pattern| msg_lower.contains(pattern)) {
                    context_info.has_context = true;
                    context_info.context_type = Some("error_troubleshooting".to_string());
                    context_info.context_strength += 2;
                }
            }
            if msg.role == "user" && msg.triggered_screenshot == Some(true) {
                context_info.recent_screenshot = true;
                context_info.context_strength += 1;
            }
            let task_indicators = ["step", "next", "then", "after", "now"];
            if task_indicators.iter().any(|&indicator| msg_lower.contains(indicator)) {
                context_info.user_in_middle_of_task = true;
                context_info.context_strength += 1;
            }
        }
        context_info
    }
    
    fn is_contextual_followup(&self, query: &str) -> bool {
        let followup_patterns = [
            "which", "what", "where", "should i", "do i", "how about",
            "what about", "is this", "does this", "can i", "may i",
            "next", "then", "now what", "ok", "okay", "like this",
            "correct", "right"
        ];
        followup_patterns.iter().any(|&pattern| {
            query.starts_with(pattern) || query.starts_with(&format!("^{}", pattern))
        })
    }
    
    fn get_base_screenshot_score(&self, query: &str) -> i32 {
        let screenshot_keywords = [
            "this", "that", "these", "those", "current", "currently", 
            "right now", "now", "here", "there", "visible", "see", 
            "seeing", "shown", "showing", "button", "popup", "dialog", 
            "menu", "which", "where", "help me"
        ];
        let mut score = 0;
        for keyword in &screenshot_keywords {
            if query.contains(keyword) {
                score += 1;
            }
        }
        let strong_indicators = ["this", "that", "current"];
        if strong_indicators.iter().any(|&word| query.contains(word)) {
            score += 2;
        }
        score
    }
    
    fn get_base_no_screenshot_score(&self, query: &str) -> i32 {
        let no_screenshot_keywords = [
            "explain", "what is", "how to", "difference between", 
            "history of", "write", "create", "generate", "timer", 
            "reminder", "weather"
        ];
        let mut score = 0;
        for keyword in &no_screenshot_keywords {
            if query.contains(keyword) {
                score += 1;
            }
        }
        score
    }
}

// Session manager for handling full conversation flow
pub struct SessionManager {
    classifier: ContextualScreenshotClassifier,
}

impl SessionManager {
    pub fn new(max_history: usize) -> Self {
        Self {
            classifier: ContextualScreenshotClassifier::new(max_history),
        }
    }
    pub fn process_user_query(&mut self, query: &str) -> ClassificationResult {
        let result = self.classifier.classify_with_context(query);
        let user_msg = ChatMessage {
            role: "user".to_string(),
            content: query.to_string(),
            timestamp: Utc::now(),
            triggered_screenshot: Some(result.needs_screenshot),
        };
        self.classifier.add_message(user_msg);
        // update result with maybe later screenshot_base64 outside
        result
    }
    pub fn add_message(&mut self, msg: ChatMessage) { self.classifier.add_message(msg); }
}
