---
license: apache-2.0
tags:
  - education
  - sklearn
  - logistic-regression
  - student-analytics
language:
  - en
---

# PRAJNA Mistake Predictor

Logistic regression model that predicts P(mistake) per student per micro-topic for NEET/JEE exams.

## Architecture

- **Model**: Scikit-learn LogisticRegression with StandardScaler
- **7 features**: rolling_accuracy, ability_score, topic_difficulty, exam_importance, avg_time_spent, streak, exam_number
- **Label**: binary (1 = student accuracy < 50% on topic in exam, 0 = OK)
- **Training**: Exams 1-8, validation on 9, test on 10

## Features

| Feature | Description | Range |
|---------|-------------|-------|
| rolling_accuracy | Avg accuracy on this topic across prior exams | 0-1 |
| ability_score | Student's subject-level baseline ability | 0-1 |
| topic_difficulty | Avg difficulty from exam DB, normalized | 0-1 |
| exam_importance | PRAJNA appearance probability for this topic | 0-1 |
| avg_time_spent | Normalized avg time on this topic | 0-1 |
| streak | Consecutive correct/wrong streak (clipped) | -1 to 1 |
| exam_number | Temporal position normalized | 0-1 |

## Outputs

- `p_mistake`: probability the student will make a mistake on this topic (0-1)
- `feature_importances`: which factors most predict mistakes

## Usage

```python
from mistake_predictor import MistakePredictor

mp = MistakePredictor()
X_train, y_train = mp.build_features(results_df, abilities_df, topic_difficulty, prajna_importance)
mp.train(X_train, y_train)

# Per-student predictions
predictions = mp.predict_for_student(results_df, abilities_df, topic_difficulty, prajna_importance, student_id="S1")
```

## Center-View Analysis

The companion `MistakeAnalyzer` provides aggregate insights:
- **Danger Zones**: topics where error_rate > threshold AND PRAJNA appearance_probability is high
- **Co-failure Patterns**: P(fail B | fail A) -- correlated topic failures
- **Time vs Accuracy**: scatter analysis revealing conceptual gaps

## License

Apache 2.0
