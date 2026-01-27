#include <bits/stdc++.h>
using namespace std;

struct Node {
    char type; // 'C', 'V', 'O'
    char val;  // for C/V: 'T'/'F' or variable letter
    char op;   // for O: '&' or '|'
    int l = -1, r = -1;
};

struct ExprBuilder {
    vector<Node> nodes;
    vector<int> varId;
    int constT = -1, constF = -1;

    int newConst(char c) {
        Node nd;
        nd.type = 'C';
        nd.val = c;
        nodes.push_back(nd);
        return (int)nodes.size() - 1;
    }
    int newVar(char c) {
        Node nd;
        nd.type = 'V';
        nd.val = c;
        nodes.push_back(nd);
        return (int)nodes.size() - 1;
    }
    int newOp(char op, int l, int r) {
        Node nd;
        nd.type = 'O';
        nd.op = op;
        nd.l = l;
        nd.r = r;
        nodes.push_back(nd);
        return (int)nodes.size() - 1;
    }

    int buildBalanced(const vector<int>& arr, int l, int r, char op) {
        if (r - l == 1) return arr[l];
        int m = (l + r) >> 1;
        int L = buildBalanced(arr, l, m, op);
        int R = buildBalanced(arr, m, r, op);
        return newOp(op, L, R);
    }

    int buildAnd(const vector<int>& parts) {
        if (parts.empty()) return constT;
        if (parts.size() == 1) return parts[0];
        return buildBalanced(parts, 0, (int)parts.size(), '&');
    }

    int buildOr(const vector<int>& parts) {
        if (parts.empty()) return constF;
        if (parts.size() == 1) return parts[0];
        return buildBalanced(parts, 0, (int)parts.size(), '|');
    }

    void print(int id, ostream& out) const {
        const Node& nd = nodes[id];
        if (nd.type == 'C' || nd.type == 'V') {
            out << nd.val;
        } else {
            out << '(';
            print(nd.l, out);
            out << nd.op;
            print(nd.r, out);
            out << ')';
        }
    }
};

static inline int pc(unsigned x) {
    return __builtin_popcount(x);
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

        if (n > 26) {
            cout << "No\n";
            continue;
        }

        int N = 1 << n;
        if ((int)s.size() != N) {
            cout << "No\n";
            continue;
        }

        vector<uint8_t> f(N);
        int ones = 0;
        for (int i = 0; i < N; i++) {
            f[i] = (s[i] == '1');
            ones += f[i];
        }

        bool mono = true;
        for (int mask = 0; mask < N && mono; mask++) {
            if (!f[mask]) continue;
            for (int i = 0; i < n; i++) {
                if (!(mask & (1 << i))) {
                    if (!f[mask | (1 << i)]) {
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

        if (ones == 0) {
            cout << "Yes\nF\n";
            continue;
        }
        if (ones == N) {
            cout << "Yes\nT\n";
            continue;
        }

        vector<int> mins;
        mins.reserve(N);
        for (int mask = 0; mask < N; mask++) {
            if (!f[mask]) continue;
            bool minimal = true;
            for (int i = 0; i < n; i++) {
                if (mask & (1 << i)) {
                    if (f[mask ^ (1 << i)]) {
                        minimal = false;
                        break;
                    }
                }
            }
            if (minimal) mins.push_back(mask);
        }

        vector<int> max0s;
        max0s.reserve(N);
        for (int mask = 0; mask < N; mask++) {
            if (f[mask]) continue;
            bool maximal = true;
            for (int i = 0; i < n; i++) {
                if (!(mask & (1 << i))) {
                    if (!f[mask | (1 << i)]) {
                        maximal = false;
                        break;
                    }
                }
            }
            if (maximal) max0s.push_back(mask);
        }

        long long dnf_ops = 0;
        {
            long long sum = 0;
            for (int m : mins) sum += pc((unsigned)m);
            dnf_ops = sum - 1;
        }

        long long cnf_ops = 0;
        {
            long long sum = 0;
            for (int m : max0s) sum += (n - pc((unsigned)m));
            cnf_ops = sum - 1;
        }

        bool useDNF = (dnf_ops <= cnf_ops);

        ExprBuilder eb;
        eb.nodes.reserve(200000);
        eb.varId.assign(n, -1);
        eb.constT = eb.newConst('T');
        eb.constF = eb.newConst('F');
        for (int i = 0; i < n; i++) eb.varId[i] = eb.newVar(char('a' + i));

        int root = -1;
        if (useDNF) {
            vector<int> terms;
            terms.reserve(mins.size());
            for (int m : mins) {
                vector<int> vs;
                vs.reserve(pc((unsigned)m));
                for (int i = 0; i < n; i++) if (m & (1 << i)) vs.push_back(eb.varId[i]);
                int term = eb.buildAnd(vs);
                terms.push_back(term);
            }
            root = eb.buildOr(terms);
        } else {
            vector<int> clauses;
            clauses.reserve(max0s.size());
            for (int m : max0s) {
                vector<int> vs;
                vs.reserve(n - pc((unsigned)m));
                for (int i = 0; i < n; i++) if (!(m & (1 << i))) vs.push_back(eb.varId[i]);
                int clause = eb.buildOr(vs);
                clauses.push_back(clause);
            }
            root = eb.buildAnd(clauses);
        }

        cout << "Yes\n";
        eb.print(root, cout);
        cout << "\n";
    }

    return 0;
}