#include <bits/stdc++.h>
using namespace std;

struct Node {
    int l = -1, r = -1;   // children ids
    int depth = -1;       // depth in decomposition (0..n-1). Not used for constants.
    char var = 0;         // variable at this node
    int ops = 0;          // minimal ops count for this node using monotone Shannon expansion
    string str;           // cached expression string (built on demand)
};

static const int ID_F = 0; // False
static const int ID_T = 1; // True

// Combine a list of strings with a binary operator using a balanced binary tree to keep depth low
static string combineBalanced(vector<string> items, char op) {
    if (items.empty()) return ""; // should not happen for valid calls
    while (items.size() > 1) {
        vector<string> next;
        next.reserve((items.size() + 1) >> 1);
        for (size_t i = 0; i < items.size(); i += 2) {
            if (i + 1 < items.size()) {
                string s;
                s.reserve(items[i].size() + items[i+1].size() + 3);
                s.push_back('(');
                s += items[i];
                s.push_back(op);
                s += items[i+1];
                s.push_back(')');
                next.emplace_back(move(s));
            } else {
                next.emplace_back(move(items[i]));
            }
        }
        items.swap(next);
    }
    return items[0];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        string s;
        cin >> n >> s;
        int N = 1 << n;

        // Quick validation for length
        if ((int)s.size() != N) {
            cout << "No\n";
            continue;
        }

        // Check monotonicity: for each i, for masks with bit i = 0, s[mask] <= s[mask|1<<i]
        bool monotone = true;
        for (int i = 0; i < n && monotone; ++i) {
            int step = 1 << i;
            for (int mask = 0; mask < N; ++mask) {
                if ((mask & step) == 0) {
                    if (s[mask] == '1' && s[mask | step] == '0') {
                        monotone = false;
                        break;
                    }
                }
            }
        }

        if (!monotone) {
            cout << "No\n";
            continue;
        }

        // Handle constants
        bool all0 = true, all1 = true;
        for (char c : s) {
            if (c == '1') all0 = false;
            else all1 = false;
        }
        if (all0) {
            cout << "Yes\nF\n";
            continue;
        }
        if (all1) {
            cout << "Yes\nT\n";
            continue;
        }

        // If n > 26, variables beyond 'z' cannot be represented by grammar; declare No.
        if (n > 26) {
            cout << "No\n";
            continue;
        }

        // Prepare variables names a..z
        auto varChar = [&](int idx0based) -> char {
            return char('a' + idx0based);
        };

        // Build minimal DNF (from minimal true points) and CNF (from maximal false points) op counts
        // Also prepare term/clauses strings only if chosen later.
        vector<int> minimalOnes;
        minimalOnes.reserve(N);
        vector<int> maximalZeros;
        maximalZeros.reserve(N);
        for (int mask = 0; mask < N; ++mask) {
            if (s[mask] == '1') {
                bool minimal = true;
                int x = mask;
                while (x) {
                    int b = x & -x;
                    int m2 = mask ^ b;
                    if (s[m2] == '1') { minimal = false; break; }
                    x ^= b;
                }
                if (minimal) minimalOnes.push_back(mask);
            } else {
                bool maximal = true;
                int inv = ((N - 1) ^ mask); // bits where mask has 0
                int x = inv;
                while (x) {
                    int b = x & -x;
                    int m2 = mask | b;
                    if (s[m2] == '0') { maximal = false; break; }
                    x ^= b;
                }
                if (maximal) maximalZeros.push_back(mask);
            }
        }

        auto popcount32 = [](unsigned x)->int{ return __builtin_popcount(x); };
        long long opsDNF = 0;
        if (!minimalOnes.empty()) {
            long long andOps = 0;
            for (int m : minimalOnes) {
                int k = popcount32((unsigned)m);
                if (k >= 1) andOps += (k - 1);
                // k==0 would be constant True but handled earlier (all1)
            }
            long long orOps = (int)minimalOnes.size() - 1;
            if (orOps < 0) orOps = 0;
            opsDNF = andOps + orOps;
        } else {
            // no minimal ones means function is F, but we handled all0 above, so shouldn't occur
            opsDNF = (long long)4e18; // sentinel large
        }

        long long opsCNF = 0;
        if (!maximalZeros.empty()) {
            long long orOpsClauses = 0;
            for (int m : maximalZeros) {
                int clauseSize = n - popcount32((unsigned)m);
                if (clauseSize >= 1) orOpsClauses += (clauseSize - 1);
                // clauseSize==0 would correspond to False clause -> whole function False, but handled already
            }
            long long andOps = (int)maximalZeros.size() - 1;
            if (andOps < 0) andOps = 0;
            opsCNF = orOpsClauses + andOps;
        } else {
            // no maximal zeros means function is T, handled already
            opsCNF = (long long)4e18;
        }

        // Build positive Shannon expansion (fixed variable order x_n, x_{n-1}, ..., x_1)
        // Segment decomposition: at depth d, there are 2^d segments each of length 2^{n-d}
        // Leaves at depth n contain the bits.
        vector<vector<int>> ids(n + 1);
        ids[n].resize(N);
        for (int j = 0; j < N; ++j) ids[n][j] = (s[j] == '1') ? ID_T : ID_F;

        vector<Node> nodes;
        nodes.reserve((1u << (min(n, 20))) + 4);
        nodes.push_back(Node()); // ID 0: F
        nodes.push_back(Node()); // ID 1: T
        nodes[ID_F].ops = 0;
        nodes[ID_T].ops = 0;

        // Maps per depth for unique nodes (excluding cases where left==right collapsed)
        vector<unordered_map<uint64_t, int>> uniq(n);
        for (int d = n - 1; d >= 0; --d) {
            int segs = 1 << d;
            ids[d].resize(segs);
            char v = varChar(n - d - 1); // variable at this depth
            uniq[d].reserve(segs * 2);
            for (int j = 0; j < segs; ++j) {
                int L = ids[d + 1][2 * j];
                int R = ids[d + 1][2 * j + 1];
                if (L == R) {
                    ids[d][j] = L;
                } else {
                    uint64_t key = (uint64_t(uint32_t(L)) << 32) | uint32_t(R);
                    auto it = uniq[d].find(key);
                    if (it != uniq[d].end()) {
                        ids[d][j] = it->second;
                    } else {
                        Node u;
                        u.l = L; u.r = R; u.depth = d; u.var = v;
                        // compute ops
                        if (L == ID_F && R == ID_T) {
                            u.ops = 0; // equals variable v
                        } else if (L == ID_F) {
                            u.ops = nodes[R].ops + 1; // (v & R)
                        } else if (R == ID_T) {
                            u.ops = nodes[L].ops + 1; // (L | v)
                        } else {
                            u.ops = nodes[L].ops + nodes[R].ops + 2; // (L | (v & R))
                        }
                        int id = (int)nodes.size();
                        nodes.push_back(move(u));
                        uniq[d][key] = id;
                        ids[d][j] = id;
                    }
                }
            }
        }
        int rootId = ids[0][0];
        long long opsPS = nodes[rootId].ops;

        // Choose the best among PS, DNF, CNF by minimal ops
        enum Form { PS_FORM, DNF_FORM, CNF_FORM };
        Form bestForm = PS_FORM;
        long long bestOps = opsPS;
        if (opsDNF < bestOps) { bestOps = opsDNF; bestForm = DNF_FORM; }
        if (opsCNF < bestOps) { bestOps = opsCNF; bestForm = CNF_FORM; }

        cout << "Yes\n";
        if (bestForm == PS_FORM) {
            // Build expression string recursively with memoization
            function<const string&(int)> buildPS = [&](int id) -> const string& {
                if (id == ID_F) { static string F = "F"; return F; }
                if (id == ID_T) { static string T = "T"; return T; }
                Node &u = nodes[id];
                if (!u.str.empty()) return u.str;
                const string &Ls = buildPS(u.l);
                const string &Rs = buildPS(u.r);
                if (u.l == ID_F && u.r == ID_T) {
                    u.str.assign(1, u.var); // variable
                } else if (u.l == ID_F) {
                    // (v & R)
                    u.str.reserve(1 + 1 + 1 + (int)Rs.size() + 1);
                    u.str.push_back('(');
                    u.str.push_back(u.var);
                    u.str.push_back('&');
                    u.str += Rs;
                    u.str.push_back(')');
                } else if (u.r == ID_T) {
                    // (L | v)
                    u.str.reserve(1 + (int)Ls.size() + 1 + 1 + 1);
                    u.str.push_back('(');
                    u.str += Ls;
                    u.str.push_back('|');
                    u.str.push_back(u.var);
                    u.str.push_back(')');
                } else {
                    // (L | (v & R))
                    u.str.reserve(1 + (int)Ls.size() + 1 + 1 + 1 + (int)Rs.size() + 2);
                    u.str.push_back('(');
                    u.str += Ls;
                    u.str.push_back('|');
                    u.str.push_back('(');
                    u.str.push_back(u.var);
                    u.str.push_back('&');
                    u.str += Rs;
                    u.str.push_back(')');
                    u.str.push_back(')');
                }
                return u.str;
            };
            const string &expr = buildPS(rootId);
            cout << expr << "\n";
        } else if (bestForm == DNF_FORM) {
            // Build DNF expression string with balanced parentheses
            vector<string> terms;
            terms.reserve(minimalOnes.size());
            for (int m : minimalOnes) {
                vector<string> vars;
                vars.reserve(n);
                for (int i = 0; i < n; ++i) if (m & (1 << i)) {
                    string v(1, varChar(i));
                    vars.push_back(move(v));
                }
                if (vars.empty()) {
                    // Shouldn't happen due to all1 handled above
                    terms.push_back("T");
                } else if (vars.size() == 1) {
                    terms.push_back(move(vars[0]));
                } else {
                    string andTerm = combineBalanced(vars, '&');
                    terms.push_back(move(andTerm));
                }
            }
            if (terms.empty()) {
                cout << "F\n";
            } else if (terms.size() == 1) {
                cout << terms[0] << "\n";
            } else {
                string expr = combineBalanced(terms, '|');
                cout << expr << "\n";
            }
        } else {
            // CNF_FORM: build CNF expression string with balanced parentheses
            vector<string> clauses;
            clauses.reserve(maximalZeros.size());
            for (int m : maximalZeros) {
                vector<string> lits;
                lits.reserve(n);
                for (int i = 0; i < n; ++i) if ((m & (1 << i)) == 0) {
                    string v(1, varChar(i));
                    lits.push_back(move(v));
                }
                if (lits.empty()) {
                    // Shouldn't happen due to all0 handled above
                    clauses.push_back("F");
                } else if (lits.size() == 1) {
                    clauses.push_back(move(lits[0]));
                } else {
                    string orClause = combineBalanced(lits, '|');
                    clauses.push_back(move(orClause));
                }
            }
            if (clauses.empty()) {
                cout << "T\n";
            } else if (clauses.size() == 1) {
                cout << clauses[0] << "\n";
            } else {
                string expr = combineBalanced(clauses, '&');
                cout << expr << "\n";
            }
        }
    }

    return 0;
}