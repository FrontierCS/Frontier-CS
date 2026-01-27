#include <bits/stdc++.h>
using namespace std;

struct ExprBuilder {
    struct Node {
        int l = -1, r = -1;
        char op = 0;   // '&' or '|' for internal; 0 for leaf
        char leaf = 0; // 'a'.. or 'T'/'F' if leaf
    };

    int n;
    vector<Node> nodes;
    vector<int> len;

    explicit ExprBuilder(int n_) : n(n_) {
        nodes.reserve(200000);
        len.reserve(200000);
    }

    int make_leaf(char c) {
        int id = (int)nodes.size();
        nodes.push_back(Node{-1, -1, 0, c});
        len.push_back(1);
        return id;
    }

    int make_op(char op, int a, int b) {
        int id = (int)nodes.size();
        nodes.push_back(Node{a, b, op, 0});
        len.push_back(len[a] + len[b] + 3);
        return id;
    }

    int combine_balanced(vector<int> items, char op) {
        if (items.empty()) return -1;
        while (items.size() > 1) {
            vector<int> nxt;
            nxt.reserve((items.size() + 1) / 2);
            for (size_t i = 0; i + 1 < items.size(); i += 2) {
                nxt.push_back(make_op(op, items[i], items[i + 1]));
            }
            if (items.size() & 1) nxt.push_back(items.back());
            items.swap(nxt);
        }
        return items[0];
    }

    int build_from_mask(int mask, char op) {
        vector<int> parts;
        parts.reserve(n);
        for (int i = 0; i < n; i++) {
            if (mask & (1 << i)) parts.push_back(make_leaf(char('a' + i)));
        }
        if (parts.empty()) {
            // Should not happen for our usage (handled by constants earlier).
            return make_leaf(op == '&' ? 'T' : 'F');
        }
        return combine_balanced(std::move(parts), op);
    }

    void append_expr(int v, string &out) const {
        const Node &nd = nodes[v];
        if (nd.op == 0) {
            out.push_back(nd.leaf);
            return;
        }
        out.push_back('(');
        append_expr(nd.l, out);
        out.push_back(nd.op);
        append_expr(nd.r, out);
        out.push_back(')');
    }

    string build_string(int root) const {
        string out;
        out.reserve((size_t)len[root]);
        append_expr(root, out);
        return out;
    }
};

static inline int popc(int x) { return __builtin_popcount((unsigned)x); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        string s;
        cin >> n >> s;
        int N = 1 << n;

        vector<uint8_t> val(N);
        bool all0 = true, all1 = true;
        for (int i = 0; i < N; i++) {
            val[i] = (s[i] == '1');
            if (val[i]) all0 = false;
            else all1 = false;
        }

        bool mono = true;
        for (int i = 0; i < n && mono; i++) {
            int bit = 1 << i;
            for (int mask = 0; mask < N; mask++) {
                if ((mask & bit) == 0) {
                    if (val[mask] && !val[mask | bit]) {
                        mono = false;
                        break;
                    }
                }
            }
        }

        if (!mono) {
            cout << "No\n";
            continue;
        }

        cout << "Yes\n";
        if (all0) {
            cout << "F\n";
            continue;
        }
        if (all1) {
            cout << "T\n";
            continue;
        }

        vector<int> minTrue;
        vector<int> maxFalse;
        minTrue.reserve(N);
        maxFalse.reserve(N);

        for (int mask = 0; mask < N; mask++) {
            if (val[mask]) {
                bool minimal = true;
                int tmp = mask;
                while (tmp) {
                    int b = __builtin_ctz((unsigned)tmp);
                    if (val[mask ^ (1 << b)]) {
                        minimal = false;
                        break;
                    }
                    tmp &= tmp - 1;
                }
                if (minimal) minTrue.push_back(mask);
            } else {
                bool maximal = true;
                for (int i = 0; i < n; i++) {
                    if ((mask & (1 << i)) == 0) {
                        if (!val[mask | (1 << i)]) {
                            maximal = false;
                            break;
                        }
                    }
                }
                if (maximal) maxFalse.push_back(mask);
            }
        }

        long long dnfOps = (long long)minTrue.size() - 1;
        for (int m : minTrue) dnfOps += (long long)popc(m) - 1;

        long long cnfOps = (long long)maxFalse.size() - 1;
        for (int m : maxFalse) cnfOps += (long long)(n - popc(m)) - 1;

        bool useDNF = (dnfOps <= cnfOps);

        ExprBuilder eb(n);
        int root = -1;

        if (useDNF) {
            vector<int> terms;
            terms.reserve(minTrue.size());
            for (int m : minTrue) terms.push_back(eb.build_from_mask(m, '&'));
            root = eb.combine_balanced(std::move(terms), '|');
        } else {
            int full = (1 << n) - 1;
            vector<int> clauses;
            clauses.reserve(maxFalse.size());
            for (int m : maxFalse) {
                int cm = full ^ m; // vars that are 0 in this maximal false assignment
                clauses.push_back(eb.build_from_mask(cm, '|'));
            }
            root = eb.combine_balanced(std::move(clauses), '&');
        }

        cout << eb.build_string(root) << "\n";
    }
    return 0;
}