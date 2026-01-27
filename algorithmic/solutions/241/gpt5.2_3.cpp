#include <bits/stdc++.h>
using namespace std;

struct ExprBuilder {
    struct Node {
        char type; // 'C', 'V', '&', '|'
        char ch;   // for 'C' and 'V'
        int l = -1, r = -1;
    };

    int n;
    vector<Node> nodes;
    int idT, idF;
    vector<int> varId;

    explicit ExprBuilder(int n_) : n(n_) {
        nodes.reserve(n + 10);
        idT = newConst('T');
        idF = newConst('F');
        varId.resize(n);
        for (int i = 0; i < n; i++) varId[i] = newVar(char('a' + i));
    }

    int newConst(char c) {
        nodes.push_back(Node{'C', c, -1, -1});
        return (int)nodes.size() - 1;
    }
    int newVar(char c) {
        nodes.push_back(Node{'V', c, -1, -1});
        return (int)nodes.size() - 1;
    }
    int newOp(char op, int l, int r) {
        nodes.push_back(Node{op, 0, l, r});
        return (int)nodes.size() - 1;
    }

    int buildBalanced(const vector<int>& ids, int L, int R, char op) {
        if (R - L == 1) return ids[L];
        int M = (L + R) >> 1;
        int left = buildBalanced(ids, L, M, op);
        int right = buildBalanced(ids, M, R, op);
        return newOp(op, left, right);
    }
    int buildBalanced(const vector<int>& ids, char op) {
        return buildBalanced(ids, 0, (int)ids.size(), op);
    }

    void toString(int root, string& out) const {
        const Node& nd = nodes[root];
        if (nd.type == 'C' || nd.type == 'V') {
            out.push_back(nd.ch);
            return;
        }
        out.push_back('(');
        toString(nd.l, out);
        out.push_back(nd.type);
        toString(nd.r, out);
        out.push_back(')');
    }
};

static inline bool isMonotoneTable(const string& s, int n) {
    int N = 1 << n;
    for (int b = 0; b < n; b++) {
        int step = 1 << b;
        int block = step << 1;
        for (int base = 0; base < N; base += block) {
            int left = base;
            int right = base + step;
            for (int off = 0; off < step; off++) {
                if (s[left + off] == '1' && s[right + off] == '0') return false;
            }
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        string s;
        cin >> n >> s;

        if (n > 26) { // cannot name variables beyond 'z'
            cout << "No\n";
            continue;
        }

        int N = 1 << n;
        if ((int)s.size() != N) {
            cout << "No\n";
            continue;
        }

        if (!isMonotoneTable(s, n)) {
            cout << "No\n";
            continue;
        }

        // Constant shortcuts (valid under monotonicity)
        if (s[0] == '1') {
            cout << "Yes\nT\n";
            continue;
        }
        if (s[N - 1] == '0') {
            cout << "Yes\nF\n";
            continue;
        }

        // Build minimal true assignments (DNF) and maximal false assignments (CNF)
        vector<int> mins;
        mins.reserve(N / 2);
        long long dnfCost = 0;
        for (int mask = 0; mask < N; mask++) {
            if (s[mask] != '1') continue;
            bool minimal = true;
            int x = mask;
            while (x) {
                int bit = __builtin_ctz((unsigned)x);
                int m2 = mask ^ (1 << bit);
                if (s[m2] == '1') {
                    minimal = false;
                    break;
                }
                x &= x - 1;
            }
            if (minimal) {
                mins.push_back(mask);
                int k = __builtin_popcount((unsigned)mask);
                if (k >= 2) dnfCost += (k - 1);
            }
        }
        if ((int)mins.size() >= 2) dnfCost += (long long)mins.size() - 1;

        vector<int> max0;
        max0.reserve(N / 2);
        long long cnfCost = 0;
        bool cnfIsFalse = false;
        for (int mask = 0; mask < N; mask++) {
            if (s[mask] != '0') continue;
            bool maximal = true;
            for (int b = 0; b < n; b++) {
                if ((mask & (1 << b)) == 0) {
                    if (s[mask | (1 << b)] == '0') {
                        maximal = false;
                        break;
                    }
                }
            }
            if (maximal) {
                max0.push_back(mask);
                int c = n - __builtin_popcount((unsigned)mask); // clause size
                if (c == 0) {
                    cnfIsFalse = true;
                    break;
                }
                if (c >= 2) cnfCost += (c - 1);
            }
        }
        if (cnfIsFalse) {
            cnfCost = 0;
            max0.clear();
            max0.push_back(N - 1); // sentinel, will output F
        } else if ((int)max0.size() >= 2) {
            cnfCost += (long long)max0.size() - 1;
        }

        bool useDNF = true;
        // If CNF yields immediate F, and DNF doesn't, choose smaller anyway.
        if (cnfIsFalse) {
            useDNF = !(dnfCost == 0); // if DNF also 0 (shouldn't), keep DNF
            if (!useDNF) useDNF = true;
        } else {
            if (cnfCost < dnfCost) useDNF = false;
        }

        ExprBuilder builder(n);
        int root = -1;
        long long ops = 0;

        if (useDNF) {
            ops = dnfCost;
            if (mins.empty()) {
                root = builder.idF;
            } else {
                vector<int> termIds;
                termIds.reserve(mins.size());
                for (int mask : mins) {
                    vector<int> vars;
                    vars.reserve(__builtin_popcount((unsigned)mask));
                    int x = mask;
                    while (x) {
                        int bit = __builtin_ctz((unsigned)x);
                        vars.push_back(builder.varId[bit]);
                        x &= x - 1;
                    }
                    int tid;
                    if (vars.empty()) {
                        tid = builder.idT;
                    } else if ((int)vars.size() == 1) {
                        tid = vars[0];
                    } else {
                        tid = builder.buildBalanced(vars, '&');
                    }
                    termIds.push_back(tid);
                }
                if ((int)termIds.size() == 1) root = termIds[0];
                else root = builder.buildBalanced(termIds, '|');
            }
        } else {
            if (cnfIsFalse) {
                root = builder.idF;
                ops = 0;
            } else if (max0.empty()) {
                root = builder.idT;
                ops = 0;
            } else {
                ops = cnfCost;
                vector<int> clauseIds;
                clauseIds.reserve(max0.size());
                for (int mask : max0) {
                    vector<int> vars;
                    vars.reserve(n);
                    for (int b = 0; b < n; b++) {
                        if ((mask & (1 << b)) == 0) vars.push_back(builder.varId[b]);
                    }
                    int cid;
                    if (vars.empty()) {
                        cid = builder.idF;
                    } else if ((int)vars.size() == 1) {
                        cid = vars[0];
                    } else {
                        cid = builder.buildBalanced(vars, '|');
                    }
                    clauseIds.push_back(cid);
                }
                if ((int)clauseIds.size() == 1) root = clauseIds[0];
                else root = builder.buildBalanced(clauseIds, '&');
            }
        }

        cout << "Yes\n";
        if (root == builder.idT) {
            cout << "T\n";
            continue;
        }
        if (root == builder.idF) {
            cout << "F\n";
            continue;
        }

        string out;
        if (ops > 0) out.reserve((size_t)min<long long>(LLONG_MAX / 2, 4 * ops + 5));
        else out.reserve(8);
        builder.toString(root, out);
        cout << out << "\n";
    }
    return 0;
}