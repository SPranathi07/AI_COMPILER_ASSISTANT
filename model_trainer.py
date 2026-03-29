import json, numpy as np, argparse, pickle, warnings
from pathlib import Path
from datetime import datetime
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
warnings.filterwarnings('ignore')

class DatasetLoader:
    def load(self, path):
        with open(path) as f: return json.load(f)['samples']
    def prepare_classification(self, samples):
        return [" ".join(s['token_sequence']) for s in samples], [0 if s['is_correct'] else 1 for s in samples]
    def prepare_error_type(self, samples):
        X,y=[],[]
        for s in samples:
            if not s['is_correct'] and s['errors']:
                X.append(" ".join(s['token_sequence'])); y.append(s['errors'][0]['error_type'])
        return X,y

class TokenFeatureExtractor:
    def __init__(self):
        self.vec = TfidfVectorizer(analyzer='word', ngram_range=(1,3), max_features=500, sublinear_tf=True)
    def fit_transform(self, seqs):
        return np.hstack([self.vec.fit_transform(seqs).toarray(), self._struct(seqs)])
    def transform(self, seqs):
        return np.hstack([self.vec.transform(seqs).toarray(), self._struct(seqs)])
    def _struct(self, seqs):
        rows=[]
        for seq in seqs:
            t=seq.split(); c=Counter(t); n=max(len(t),1)
            rows.append([n, c.get('SEMICOLON',0), c.get('LBRACE',0), c.get('RBRACE',0),
                         c.get('LPAREN',0), c.get('RPAREN',0),
                         c.get('LBRACE',0)-c.get('RBRACE',0),
                         c.get('LPAREN',0)-c.get('RPAREN',0),
                         c.get('KEYWORD',0)/n, c.get('IDENTIFIER',0)/n,
                         c.get('OP_ASSIGN',0), c.get('OP_EQ',0), c.get('UNKNOWN',0)])
        return np.array(rows)

MODELS = {
    "Logistic Regression": LogisticRegression(max_iter=1000,C=1.0,random_state=42),
    "Random Forest":       RandomForestClassifier(n_estimators=100,max_depth=10,random_state=42),
    "Gradient Boosting":   GradientBoostingClassifier(n_estimators=100,learning_rate=0.1,random_state=42),
    "SVM":                 SVC(kernel='rbf',C=1.0,probability=True,random_state=42),
}

class ModelTrainer:
    def __init__(self):
        self.ext=TokenFeatureExtractor(); self.results={}
        self.best_model=None; self.best_name=None; self.best_score=0.0

    def train_and_evaluate(self, X, y, task):
        print(f"\n{'='*60}\n  TASK: {task}\n{'='*60}")
        print(f"  Samples: {len(X)}  |  Classes: {sorted(set(y))}\n")
        Xf = self.ext.fit_transform(X)
        # Safe CV: use KFold with max folds = min class size (at least 2)
        min_class = min(Counter(y).values())
        cv_k = max(2, min(3, min_class))
        kf = KFold(n_splits=cv_k, shuffle=True, random_state=42)
        tr = {}
        for name, model in MODELS.items():
            cv = cross_val_score(model, Xf, y, cv=kf, scoring='accuracy')
            model.fit(Xf, y); yp = model.predict(Xf)
            acc  = accuracy_score(y, yp)
            prec = precision_score(y, yp, average='weighted', zero_division=0)
            rec  = recall_score(y, yp, average='weighted', zero_division=0)
            f1   = f1_score(y, yp, average='weighted', zero_division=0)
            tr[name] = {"accuracy":round(acc,4),"precision":round(prec,4),
                        "recall":round(rec,4),"f1_score":round(f1,4),
                        "cv_mean":round(cv.mean(),4),"cv_std":round(cv.std(),4)}
            print(f"  [{name}]")
            print(f"    Accuracy:  {acc:.4f}   CV: {cv.mean():.4f} +/- {cv.std():.4f}")
            print(f"    Precision: {prec:.4f}   Recall: {rec:.4f}   F1: {f1:.4f}\n")
            if cv.mean() > self.best_score:
                self.best_score=cv.mean(); self.best_model=model; self.best_name=name
        self.results[task] = tr
        best = max(tr, key=lambda k: tr[k]['cv_mean'])
        print(f"  Best: {best}  (CV={tr[best]['cv_mean']:.4f})")
        return tr

    def save_model(self, path):
        with open(path,'wb') as f:
            pickle.dump({'model':self.best_model,'extractor':self.ext,
                         'name':self.best_name,'score':self.best_score}, f)
        print(f"\n  Model saved -> {path}")

    def save_metrics(self, path):
        r = {"generated_at":datetime.now().isoformat(),"best_model":self.best_name,
             "best_cv_score":round(self.best_score,4),"task_results":self.results}
        with open(path,'w') as f: json.dump(r,f,indent=2)
        print(f"  Metrics saved -> {path}")

EXPLANATIONS = {
    "MISSING_SEMICOLON":       {"text":"You forgot a semicolon ';' at the end of a statement. In C, every statement must end with ';'.","fix":"Add ';' at the end of the line."},
    "UNMATCHED_LBRACE":        {"text":"You opened '{' but never closed it. Every '{' needs a matching '}'.","fix":"Add '}' at the end of the block."},
    "UNMATCHED_RBRACE":        {"text":"There is an extra '}' with no matching '{'. Remove it or add the missing '{'.","fix":"Remove the extra '}'."},
    "UNMATCHED_LPAREN":        {"text":"You opened '(' but never closed it. Every '(' needs a matching ')'.","fix":"Add ')' to close the parenthesis."},
    "UNMATCHED_RPAREN":        {"text":"There is an extra ')' with no matching '('. Remove it or add '('.","fix":"Remove the extra ')'."},
    "ASSIGNMENT_IN_CONDITION": {"text":"You used '=' (assignment) in a condition. You probably meant '==' (comparison). In C, '=' sets a value while '==' checks equality.","fix":"Change '=' to '==' inside the if/while condition."},
}
AUTOCOMPLETE = {
    "KEYWORD":["IDENTIFIER","LPAREN"],"IDENTIFIER":["OP_ASSIGN","LPAREN","SEMICOLON"],
    "OP_ASSIGN":["INTEGER","FLOAT","IDENTIFIER"],"INTEGER":["SEMICOLON","OP_PLUS","RPAREN"],
    "LPAREN":["IDENTIFIER","INTEGER","KEYWORD"],"LBRACE":["KEYWORD","IDENTIFIER","RBRACE"],
    "SEMICOLON":["KEYWORD","IDENTIFIER","RBRACE"],
}

class ErrorExplainer:
    def explain(self, error_type, line):
        info = EXPLANATIONS.get(error_type, {"text":f"Unknown error '{error_type}'.","fix":"Review code near this line."})
        return {"error_type":error_type,"line":line,"explanation":info["text"],"fix":info["fix"]}
    def suggest(self, seq):
        return AUTOCOMPLETE.get(seq[-1] if seq else "", ["SEMICOLON","RBRACE"])

def main():
    ap = argparse.ArgumentParser(description="Week 9: AI Model Trainer")
    ap.add_argument('--train',    action='store_true')
    ap.add_argument('--evaluate', action='store_true')
    ap.add_argument('--all',      action='store_true')
    ap.add_argument('--dataset',  default='dataset.json')
    ap.add_argument('--out',      default='.')
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    loader  = DatasetLoader()
    samples = loader.load(args.dataset)
    print(f"\n  Loaded {len(samples)} samples from {args.dataset}")
    trainer = ModelTrainer()
    if args.train or args.all:
        X1,y1 = loader.prepare_classification(samples)
        trainer.train_and_evaluate(X1, y1, "Binary Classification (Correct vs Incorrect)")
        X2,y2 = loader.prepare_error_type(samples)
        if len(set(y2)) > 1:
            trainer.train_and_evaluate(X2, y2, "Error Type Classification")
        trainer.save_model(str(out / "model.pkl"))
        trainer.save_metrics(str(out / "metrics.json"))
    if args.evaluate or args.all:
        ex = ErrorExplainer()
        print(f"\n{'='*60}\n  DEMO - Error Explanations\n{'='*60}")
        for et in ["MISSING_SEMICOLON","ASSIGNMENT_IN_CONDITION","UNMATCHED_LBRACE"]:
            r = ex.explain(et, line=3)
            print(f"\n  {r['error_type']} @ line {r['line']}")
            print(f"  -> {r['explanation']}")
            print(f"  Fix: {r['fix']}")
        print(f"\n{'='*60}\n  DEMO - Autocomplete Suggestions\n{'='*60}")
        for seq in [["KEYWORD","IDENTIFIER","OP_ASSIGN"],["KEYWORD","LPAREN"],["SEMICOLON"]]:
            print(f"  After [{' '.join(seq)}]  ->  suggest: {ex.suggest(seq)}")

if __name__ == "__main__":
    main()