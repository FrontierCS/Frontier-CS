#include <bits/stdc++.h>
using namespace std;

struct Expr {
    string s;
    int ops;
    int depth;
};

static inline Expr makeConst(bool v){
    return {v ? "T" : "F", 0, 0};
}
static inline Expr makeVar(int idx1based){
    char c = char('a' + (idx1based - 1));
    return {string(1, c), 0, 0};
}
static inline bool isConstT(const Expr& e){ return e.s == "T"; }
static inline bool isConstF(const Expr& e){ return e.s == "F"; }

static inline Expr combine_and(const Expr& A, const Expr& B){
    if (isConstF(A) || isConstF(B)) return makeConst(false);
    if (isConstT(A)) return B;
    if (isConstT(B)) return A;
    if (A.s == B.s) return A;
    Expr r;
    r.s = "(" + A.s + "&" + B.s + ")";
    r.ops = A.ops + B.ops + 1;
    r.depth = max(A.depth, B.depth) + 1;
    return r;
}
static inline Expr combine_or(const Expr& A, const Expr& B){
    if (isConstT(A) || isConstT(B)) return makeConst(true);
    if (isConstF(A)) return B;
    if (isConstF(B)) return A;
    if (A.s == B.s) return A;
    Expr r;
    r.s = "(" + A.s + "|" + B.s + ")";
    r.ops = A.ops + B.ops + 1;
    r.depth = max(A.depth, B.depth) + 1;
    return r;
}

// split s (truth table) by variable at position pos (0-based in current vars order)
// s length = 2^k, returns g0 (xi=0) and g1 (xi=1), each length 2^(k-1)
// LSB variable toggles fastest (pos 0)
static inline void splitByPos(const string& s, int pos, string& g0, string& g1){
    int L = (int)s.size();
    int step = 1 << pos;
    int period = step << 1;
    g0.clear(); g1.clear();
    g0.reserve(L >> 1);
    g1.reserve(L >> 1);
    for(int start = 0; start < L; start += period){
        g0.append(s, start, step);
        g1.append(s, start + step, step);
    }
}

static inline int countOnes(const string& s){
    int c = 0;
    for(char ch: s) if (ch == '1') ++c;
    return c;
}

struct Builder {
    // Recursively build expression for monotone function represented by truth table s over variables 'vars' (1-based indices in ascending order)
    // Greedy variable selection with simple heuristics, with algebraic simplifications.
    Expr build(const vector<int>& vars, const string& s){
        int L = (int)s.size();
        int ones = countOnes(s);
        if (ones == 0) return makeConst(false);
        if (ones == L) return makeConst(true);
        int k = (int)vars.size();
        if (k == 0){
            // Shouldn't happen except constants already handled
            return makeConst(false);
        }

        // Try to eliminate independent variables (g0 == g1)
        for(int i = 0; i < k; ++i){
            string g0, g1;
            splitByPos(s, i, g0, g1);
            if (g0 == g1){
                vector<int> vars2;
                vars2.reserve(k - 1);
                for(int j = 0; j < k; ++j) if (j != i) vars2.push_back(vars[j]);
                return build(vars2, g0);
            }
        }

        // Precompute splits and ones counts for heuristic selection
        vector<string> g0s(k), g1s(k);
        vector<int> o0(k), o1(k);
        vector<char> g0all0(k, 0), g1all1(k, 0);
        for(int i = 0; i < k; ++i){
            splitByPos(s, i, g0s[i], g1s[i]);
            o0[i] = countOnes(g0s[i]);
            o1[i] = countOnes(g1s[i]);
            g0all0[i] = (o0[i] == 0);
            g1all1[i] = (o1[i] == (int)g1s[i].size());
        }

        // Choose variable index with heuristics
        int best = -1;

        // Priority 1: g0 == F (so f = xi & g1)
        for(int i = 0; i < k; ++i){
            if (g0all0[i]){
                if (best == -1) best = i;
                else{
                    // prefer smaller expected cost: smaller ops ~ fewer ones in g1
                    if (o1[i] < o1[best]) best = i;
                }
            }
        }
        // Priority 2: g1 == T (so f = xi | g0)
        if (best == -1){
            for(int i = 0; i < k; ++i){
                if (g1all1[i]){
                    if (best == -1) best = i;
                    else{
                        if (o0[i] < o0[best]) best = i;
                    }
                }
            }
        }
        // Priority 3: general case - pick i minimizing o0 + o1 (crude proxy)
        if (best == -1){
            int bestScore = INT_MAX;
            for(int i = 0; i < k; ++i){
                int sc = o0[i] + o1[i];
                if (sc < bestScore){
                    bestScore = sc;
                    best = i;
                }
            }
        }

        // Recurse
        vector<int> vars2;
        vars2.reserve(k - 1);
        for(int j = 0; j < k; ++j) if (j != best) vars2.push_back(vars[j]);
        Expr e1 = build(vars2, g1s[best]);
        Expr e0 = build(vars2, g0s[best]);

        // Simplify cases
        if (e1.s == e0.s) return e0;

        Expr xi = makeVar(vars[best]);

        Expr left = combine_and(xi, e1);
        Expr res = combine_or(left, e0);

        // Depth guard (should be <= 100 as per guarantee)
        // No explicit enforcement; rely on problem's guarantee.

        return res;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin >> T)) return 0;
    while(T--){
        int n;
        string s;
        cin >> n;
        cin >> s;
        int L = (int)s.size();
        // Verify length matches 2^n (assumed correct by problem)
        // Check monotonicity and dependency
        bool monotone = true;
        vector<char> depends(n, 0);
        for(int i = 0; i < n; ++i){
            int step = 1 << i;
            int period = step << 1;
            for(int start = 0; start < L; start += period){
                for(int j = 0; j < step; ++j){
                    char c0 = s[start + j];
                    char c1 = s[start + j + step];
                    if (c0 > c1) monotone = false;
                    if (c0 != c1) depends[i] = 1;
                    if (!monotone) break;
                }
                if (!monotone) break;
            }
            if (!monotone) break;
        }

        if (!monotone){
            cout << "No\n";
            continue;
        }

        // If depends on variables beyond 'z', impossible
        bool okVars = true;
        for(int i = 26; i < n; ++i){
            if (depends[i]){
                okVars = false;
                break;
            }
        }
        if (!okVars){
            cout << "No\n";
            continue;
        }

        // Reduce away variables beyond 26 (since f independent of them)
        // Also we can reduce away any variable independent at top to shrink table.
        vector<int> vars;
        vars.reserve(min(n, 26));
        for(int i = 0; i < min(n, 26); ++i) vars.push_back(i + 1);

        // First drop variables beyond 26 (guaranteed independent)
        // Then also drop independent vars among first 26 to shrink initial table
        // We'll iteratively remove any independent variable to get smaller s.
        // But independence on reduced table remains true w.r.t. original since we only drop independent dims.
        // For correctness, we should check independence on current s: we can recompute for each var in 'vars'
        // Drop any var where g0==g1; repeat until none drops.
        // Start with dropping vars >26: since independence guaranteed, we can drop them without recomputation.
        // We'll just ignore them as they are not in 'vars'; s remains same covering n vars, but we can project them out for efficiency.
        // Project all i in [27..n] out by taking any half (since g0==g1).
        if (n > 26){
            // Need to drop variables with index > 26 from s
            // We'll do it one by one from highest to lowest to keep position mapping consistent.
            // We maintain a vector 'allVars' of size current_k representing original indices in order 1..n
            vector<int> allVars(n);
            iota(allVars.begin(), allVars.end(), 1);
            string cur = s;
            for(int remIdx = n; remIdx >= 27; --remIdx){
                // find position of remIdx in allVars
                int pos = remIdx - 1; // since allVars is in ascending 1..current_k
                // split by pos
                string g0, g1;
                splitByPos(cur, pos, g0, g1);
                // since independent, g0==g1; but to be safe, pick g0
                cur = g0;
                allVars.erase(allVars.begin() + pos);
            }
            // Now cur corresponds to vars 1..min(n,26)
            s = cur;
            // L updated
            L = (int)s.size();
        }

        // Further drop independent variables among first 26 to reduce initial problem
        {
            vector<int> currVars = vars;
            string cur = s;
            while(true){
                bool dropped = false;
                for(int i = 0; i < (int)currVars.size(); ++i){
                    string g0, g1;
                    splitByPos(cur, i, g0, g1);
                    if (g0 == g1){
                        vector<int> nv;
                        nv.reserve(currVars.size() - 1);
                        for(int j = 0; j < (int)currVars.size(); ++j) if (j != i) nv.push_back(currVars[j]);
                        cur = g0;
                        currVars.swap(nv);
                        dropped = true;
                        break;
                    }
                }
                if (!dropped) break;
            }
            vars.swap(currVars);
            s.swap(cur);
            L = (int)s.size();
        }

        // Build expression
        Builder builder;
        Expr res = builder.build(vars, s);

        // Verify depth constraint (should satisfy according to problem's guarantee)
        if (res.depth > 100){
            // As a fallback, just print No (should not happen per problem statement)
            cout << "No\n";
            continue;
        }

        cout << "Yes\n";
        cout << res.s << "\n";
    }
    return 0;
}