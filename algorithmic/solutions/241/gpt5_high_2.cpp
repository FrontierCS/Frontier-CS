#include <bits/stdc++.h>
using namespace std;

struct ExprBuilder {
    struct Node {
        char type; // 'v','t','f','&','|'
        int l, r;  // children indices for '&' and '|'
        int var;   // variable index for 'v'
    };
    vector<Node> nodes;
    vector<int> varNode; // node id for each variable
    int constT, constF;

    ExprBuilder(int n) {
        nodes.reserve(100000);
        varNode.resize(n);
        for (int i = 0; i < n; ++i) {
            Node nd; nd.type = 'v'; nd.l = nd.r = -1; nd.var = i;
            nodes.push_back(nd);
            varNode[i] = (int)nodes.size() - 1;
        }
        Node t; t.type = 't'; t.l = t.r = -1; t.var = -1;
        nodes.push_back(t);
        constT = (int)nodes.size() - 1;
        Node f; f.type = 'f'; f.l = f.r = -1; f.var = -1;
        nodes.push_back(f);
        constF = (int)nodes.size() - 1;
    }
    int newOp(char op, int a, int b) {
        Node nd; nd.type = op; nd.l = a; nd.r = b; nd.var = -1;
        nodes.push_back(nd);
        return (int)nodes.size() - 1;
    }
    int buildBalanced(const vector<int>& ids, char op) {
        if (ids.empty()) return op == '&' ? constT : constF; // Shouldn't be used in our construction
        if (ids.size() == 1) return ids[0];
        vector<int> cur = ids;
        while (cur.size() > 1) {
            vector<int> nxt;
            nxt.reserve((cur.size() + 1) / 2);
            for (size_t i = 0; i < cur.size(); i += 2) {
                if (i + 1 < cur.size()) {
                    nxt.push_back(newOp(op, cur[i], cur[i + 1]));
                } else {
                    nxt.push_back(cur[i]);
                }
            }
            cur.swap(nxt);
        }
        return cur[0];
    }
    void printNode(int idx, ostream& out) {
        const Node& nd = nodes[idx];
        if (nd.type == 'v') {
            out.put(char('a' + nd.var));
        } else if (nd.type == 't') {
            out.put('T');
        } else if (nd.type == 'f') {
            out.put('F');
        } else {
            out.put('(');
            printNode(nd.l, out);
            out.put(nd.type);
            printNode(nd.r, out);
            out.put(')');
        }
    }
};

static inline int popc(int x) { return __builtin_popcount((unsigned)x); }

// Check monotonicity: for each i, for all masks with bit i set, f[mask^bit] <= f[mask]
bool is_monotone(const string& s, int n) {
    int L = 1 << n;
    for (int i = 0; i < n; ++i) {
        int bit = 1 << i;
        for (int m = 0; m < L; ++m) {
            if (m & bit) {
                if (s[m ^ bit] == '1' && s[m] == '0') return false;
            }
        }
    }
    return true;
}

// Compute cost and counts for DNF using minimal 1-elements
pair<long long,int> cost_DNF(const string& s, int n) {
    int L = 1 << n;
    int terms = 0;
    long long cost = 0;
    for (int m = 0; m < L; ++m) {
        if (s[m] == '1') {
            if (m == 0) {
                // Constant T, handled outside; here would imply all ones
                continue;
            }
            bool minimal = true;
            int t = m;
            while (t) {
                int i = __builtin_ctz(t);
                t &= (t - 1);
                if (s[m ^ (1 << i)] == '1') { minimal = false; break; }
            }
            if (minimal) {
                ++terms;
                cost += popc(m) - 1; // ANDs inside term
            }
        }
    }
    if (terms == 0) {
        // if there is no 1 at all -> F; else all ones then 0-term DNF equals F (but constant handled separately)
        // Here return 0 cost and 0 terms; caller will handle constants.
        return {0LL, 0};
    }
    cost += (terms - 1); // ORs to combine terms
    return {cost, terms};
}

// Compute cost and counts for CNF using maximal 0-elements
pair<long long,int> cost_CNF(const string& s, int n) {
    int L = 1 << n;
    int clauses = 0;
    long long cost = 0;
    for (int m = 0; m < L; ++m) {
        if (s[m] == '0') {
            if (m == L - 1) {
                // all ones mask, could be constant F; handled outside
                continue;
            }
            bool maximal = true;
            // Check immediate supersets
            for (int i = 0; i < n; ++i) {
                if ((m & (1 << i)) == 0) {
                    if (s[m | (1 << i)] == '0') { maximal = false; break; }
                }
            }
            if (maximal) {
                ++clauses;
                int k = n - popc(m); // number of zeros bits -> clause size
                cost += (k - 1); // ORs in clause
            }
        }
    }
    if (clauses == 0) {
        // If no zero -> T; else all zero handled separately
        return {0LL, 0};
    }
    cost += (clauses - 1); // ANDs to combine clauses
    return {cost, clauses};
}

// Build DNF expression using minimal 1-elements
int build_DNF(const string& s, int n, const vector<int>& varMap, ExprBuilder& B) {
    int L = 1 << n;
    vector<int> termNodes;
    termNodes.reserve(L);
    for (int m = 0; m < L; ++m) {
        if (s[m] == '1') {
            if (m == 0) {
                // constant T; should be handled before calling
                continue;
            }
            bool minimal = true;
            int t = m;
            while (t) {
                int i = __builtin_ctz(t);
                t &= (t - 1);
                if (s[m ^ (1 << i)] == '1') { minimal = false; break; }
            }
            if (minimal) {
                vector<int> lits;
                lits.reserve(popc(m));
                for (int i = 0; i < n; ++i) if (m & (1 << i)) {
                    lits.push_back(B.varNode[varMap[i]]);
                }
                int term = B.buildBalanced(lits, '&');
                termNodes.push_back(term);
            }
        }
    }
    if (termNodes.empty()) return B.constF;
    if (termNodes.size() == 1) return termNodes[0];
    return B.buildBalanced(termNodes, '|');
}

// Build CNF expression using maximal 0-elements
int build_CNF(const string& s, int n, const vector<int>& varMap, ExprBuilder& B) {
    int L = 1 << n;
    vector<int> clauseNodes;
    clauseNodes.reserve(L);
    for (int m = 0; m < L; ++m) {
        if (s[m] == '0') {
            if (m == L - 1) {
                // All ones vector: constant F; should be handled before calling
                continue;
            }
            bool maximal = true;
            for (int i = 0; i < n; ++i) if ((m & (1 << i)) == 0) {
                if (s[m | (1 << i)] == '0') { maximal = false; break; }
            }
            if (maximal) {
                vector<int> lits;
                lits.reserve(n - popc(m));
                for (int i = 0; i < n; ++i) if ((m & (1 << i)) == 0) {
                    lits.push_back(B.varNode[varMap[i]]);
                }
                int clause = B.buildBalanced(lits, '|');
                clauseNodes.push_back(clause);
            }
        }
    }
    if (clauseNodes.empty()) return B.constT;
    if (clauseNodes.size() == 1) return clauseNodes[0];
    return B.buildBalanced(clauseNodes, '&');
}

pair<long long,int> best_cost_base(const string& s, int n) {
    int L = 1 << n;
    bool all0 = true, all1 = true;
    for (int i = 0; i < L; ++i) {
        if (s[i] == '1') all0 = false;
        else all1 = false;
    }
    if (all1) return {0LL, 2}; // let caller handle constants
    if (all0) return {0LL, 2};
    auto cd = cost_DNF(s, n);
    auto cc = cost_CNF(s, n);
    if (cd.first <= cc.first) return cd;
    return cc;
}

int build_best_base(const string& s, int n, const vector<int>& varMap, ExprBuilder& B) {
    int L = 1 << n;
    bool all0 = true, all1 = true;
    for (int i = 0; i < L; ++i) {
        if (s[i] == '1') all0 = false;
        else all1 = false;
    }
    if (all1) return B.constT;
    if (all0) return B.constF;
    auto cd = cost_DNF(s, n);
    auto cc = cost_CNF(s, n);
    if (cd.first <= cc.first) {
        return build_DNF(s, n, varMap, B);
    } else {
        return build_CNF(s, n, varMap, B);
    }
}

// Split truth table by variable at index 'vIdx' (0-based), produce s0 and s1 of length 2^(n-1)
void split_by_var(const string& s, int n, int vIdx, string& s0, string& s1) {
    int L = 1 << n;
    int M = L >> 1;
    s0.resize(M);
    s1.resize(M);
    int lowMask = (1 << vIdx) - 1;
    for (int k = 0; k < M; ++k) {
        int low = k & lowMask;
        int high = k >> vIdx;
        int idx0 = low | (high << (vIdx + 1));
        s0[k] = s[idx0];
        s1[k] = s[idx0 | (1 << vIdx)];
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        string s;
        cin >> n;
        cin >> s;
        int L = 1 << n;
        if ((int)s.size() != L) {
            cout << "No\n";
            continue;
        }
        if (!is_monotone(s, n)) {
            cout << "No\n";
            continue;
        }
        cout << "Yes\n";
        // Constants
        bool all0 = true, all1 = true;
        for (char c : s) {
            if (c == '1') all0 = false;
            else all1 = false;
        }
        ExprBuilder builder(n);
        vector<int> varMap(n);
        iota(varMap.begin(), varMap.end(), 0);

        if (all1) {
            builder.printNode(builder.constT, cout);
            cout << '\n';
            continue;
        }
        if (all0) {
            builder.printNode(builder.constF, cout);
            cout << '\n';
            continue;
        }

        // Base cost
        auto baseCost = best_cost_base(s, n);
        long long bestTotalCost = baseCost.first;
        int bestVar = -1;
        // Try single-level factoring on each variable
        for (int i = 0; i < n; ++i) {
            string s0, s1;
            split_by_var(s, n, i, s0, s1);
            // Costs for subparts
            // Handle constants of halves
            bool s0_all0 = true, s0_all1 = true;
            for (char c : s0) { if (c == '1') s0_all0 = false; else s0_all1 = false; }
            bool s1_all0 = true, s1_all1 = true;
            for (char c : s1) { if (c == '1') s1_all0 = false; else s1_all1 = false; }

            long long c0 = 0, c1 = 0;
            if (!s0_all0 && !s0_all1) c0 = best_cost_base(s0, n - 1).first;
            if (!s1_all0 && !s1_all1) c1 = best_cost_base(s1, n - 1).first;

            // Combine costs with simplifications
            long long total = 0;
            if (s0_all0 && s1_all0) {
                total = 0; // F
            } else if (s0_all1 && s1_all1) {
                total = 0; // T
            } else if (s0 == s1) {
                total = c0; // same function
            } else {
                if (s0_all0) {
                    if (s1_all1) {
                        total = 0; // x_i
                    } else {
                        total = c1 + 1; // x_i & expr1
                    }
                } else if (s1_all1) {
                    if (s0_all0) {
                        total = 0; // x_i
                    } else {
                        total = c0 + 1; // x_i | expr0
                    }
                } else if (s1_all0) {
                    // f = expr0
                    total = c0;
                } else {
                    // general: (x_i & expr1) | expr0
                    total = c1 + 1 + c0 + 1;
                }
            }
            if (total < bestTotalCost) {
                bestTotalCost = total;
                bestVar = i;
            }
        }

        int root = -1;
        if (bestVar == -1) {
            root = build_best_base(s, n, varMap, builder);
        } else {
            // Build using bestVar factoring
            string s0, s1;
            split_by_var(s, n, bestVar, s0, s1);
            // New var map excluding bestVar
            vector<int> subMap;
            subMap.reserve(n - 1);
            for (int i = 0; i < n; ++i) if (i != bestVar) subMap.push_back(varMap[i]);

            // Build sub-expressions
            // Determine constants
            bool s0_all0 = true, s0_all1 = true;
            for (char c : s0) { if (c == '1') s0_all0 = false; else s0_all1 = false; }
            bool s1_all0 = true, s1_all1 = true;
            for (char c : s1) { if (c == '1') s1_all0 = false; else s1_all1 = false; }

            int e0 = -1, e1 = -1;
            if (s0_all0) e0 = builder.constF;
            else if (s0_all1) e0 = builder.constT;
            else e0 = build_best_base(s0, n - 1, subMap, builder);

            if (s1_all0) e1 = builder.constF;
            else if (s1_all1) e1 = builder.constT;
            else e1 = build_best_base(s1, n - 1, subMap, builder);

            // Combine with simplifications
            if (e0 == builder.constF && e1 == builder.constF) {
                root = builder.constF;
            } else if (e0 == builder.constT && e1 == builder.constT) {
                root = builder.constT;
            } else if (e0 == e1) {
                root = e0;
            } else {
                int xi = builder.varNode[varMap[bestVar]];
                if (e0 == builder.constF) {
                    if (e1 == builder.constT) root = xi;
                    else root = builder.newOp('&', xi, e1);
                } else if (e1 == builder.constT) {
                    if (e0 == builder.constF) root = xi;
                    else root = builder.newOp('|', xi, e0);
                } else if (e1 == builder.constF) {
                    root = e0;
                } else {
                    int left = builder.newOp('&', xi, e1);
                    root = builder.newOp('|', left, e0);
                }
            }
        }

        builder.printNode(root, cout);
        cout << '\n';
    }
    return 0;
}