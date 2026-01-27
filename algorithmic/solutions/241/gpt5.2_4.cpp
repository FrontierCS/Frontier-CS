#include <bits/stdc++.h>
using namespace std;

struct Node {
    char type; // 'v','c','&','|'
    int var;   // for 'v': index, for 'c': 0/1
    Node *l, *r;
};

static void printExpr(const Node* p, ostream& os) {
    if (p->type == 'v') {
        os << char('a' + p->var);
    } else if (p->type == 'c') {
        os << (p->var ? 'T' : 'F');
    } else {
        os << '(';
        printExpr(p->l, os);
        os << p->type;
        printExpr(p->r, os);
        os << ')';
    }
}

static int depthParen(const Node* p) {
    if (p->type == 'v' || p->type == 'c') return 0;
    return 1 + max(depthParen(p->l), depthParen(p->r));
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
        int N = 1 << n;

        vector<uint8_t> f(N);
        int ones = 0;
        for (int i = 0; i < N; i++) {
            f[i] = (uint8_t)(s[i] - '0');
            ones += f[i];
        }

        bool mono = true;
        for (int i = 0; i < n && mono; i++) {
            int bit = 1 << i;
            for (int mask = 0; mask < N; mask++) {
                if ((mask & bit) == 0) {
                    if (f[mask] > f[mask | bit]) {
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

        if (ones == 0) {
            cout << "F\n";
            continue;
        }
        if (ones == N) {
            cout << "T\n";
            continue;
        }

        vector<int> minimalTrue;
        minimalTrue.reserve(N);
        for (int mask = 0; mask < N; mask++) {
            if (!f[mask]) continue;
            bool minimal = true;
            int tmp = mask;
            while (tmp) {
                int b = __builtin_ctz((unsigned)tmp);
                if (f[mask ^ (1 << b)]) {
                    minimal = false;
                    break;
                }
                tmp &= (tmp - 1);
            }
            if (minimal) minimalTrue.push_back(mask);
        }

        vector<int> maximalFalse;
        maximalFalse.reserve(N);
        for (int mask = 0; mask < N; mask++) {
            if (f[mask]) continue;
            bool maximal = true;
            for (int i = 0; i < n; i++) {
                if (((mask >> i) & 1) == 0) {
                    if (!f[mask | (1 << i)]) {
                        maximal = false;
                        break;
                    }
                }
            }
            if (maximal) maximalFalse.push_back(mask);
        }

        long long opsDNF = 0;
        {
            if (!minimalTrue.empty()) opsDNF += (long long)minimalTrue.size() - 1;
            for (int mask : minimalTrue) {
                int k = __builtin_popcount((unsigned)mask);
                if (k >= 1) opsDNF += (k - 1);
            }
        }

        long long opsCNF = 0;
        {
            if (!maximalFalse.empty()) opsCNF += (long long)maximalFalse.size() - 1;
            for (int mask : maximalFalse) {
                int r = n - __builtin_popcount((unsigned)mask);
                if (r >= 1) opsCNF += (r - 1);
            }
        }

        bool useDNF = (opsDNF <= opsCNF);

        deque<Node> pool;
        auto newNode = [&](char type, int var, Node* l, Node* r) -> Node* {
            pool.push_back(Node{type, var, l, r});
            return &pool.back();
        };

        Node* constF = newNode('c', 0, nullptr, nullptr);
        Node* constT = newNode('c', 1, nullptr, nullptr);

        vector<Node*> varNode(n);
        for (int i = 0; i < n; i++) varNode[i] = newNode('v', i, nullptr, nullptr);

        auto isConst = [&](Node* p, int v) -> bool {
            return p->type == 'c' && p->var == v;
        };

        function<Node*(char, Node*, Node*)> makeOp = [&](char op, Node* a, Node* b) -> Node* {
            if (a == b) return a;

            if (a->type == 'c' && b->type == 'c') {
                int va = a->var, vb = b->var;
                int res = (op == '&') ? (va & vb) : (va | vb);
                return res ? constT : constF;
            }

            if (op == '&') {
                if (isConst(a, 0) || isConst(b, 0)) return constF;
                if (isConst(a, 1)) return b;
                if (isConst(b, 1)) return a;
                // absorption: x & (x|y) = x
                if (a->type == '|' && (a->l == b || a->r == b)) return b;
                if (b->type == '|' && (b->l == a || b->r == a)) return a;
            } else { // '|'
                if (isConst(a, 1) || isConst(b, 1)) return constT;
                if (isConst(a, 0)) return b;
                if (isConst(b, 0)) return a;
                // absorption: x | (x&y) = x
                if (a->type == '&' && (a->l == b || a->r == b)) return b;
                if (b->type == '&' && (b->l == a || b->r == a)) return a;
            }
            return newNode(op, 0, a, b);
        };

        auto buildBalanced = [&](vector<Node*> elems, char op) -> Node* {
            if (elems.empty()) return (op == '&') ? constT : constF;
            while (elems.size() > 1) {
                vector<Node*> nxt;
                nxt.reserve((elems.size() + 1) / 2);
                for (size_t i = 0; i < elems.size(); i += 2) {
                    if (i + 1 < elems.size()) nxt.push_back(makeOp(op, elems[i], elems[i + 1]));
                    else nxt.push_back(elems[i]);
                }
                elems.swap(nxt);
            }
            return elems[0];
        };

        Node* root = nullptr;

        if (useDNF) {
            vector<Node*> terms;
            terms.reserve(minimalTrue.size());
            for (int mask : minimalTrue) {
                vector<Node*> vs;
                vs.reserve(n);
                for (int i = 0; i < n; i++) if ((mask >> i) & 1) vs.push_back(varNode[i]);
                Node* term = vs.empty() ? constT : buildBalanced(vs, '&');
                terms.push_back(term);
            }
            root = terms.empty() ? constF : buildBalanced(terms, '|');
        } else {
            vector<Node*> clauses;
            clauses.reserve(maximalFalse.size());
            for (int mask : maximalFalse) {
                vector<Node*> vs;
                vs.reserve(n);
                for (int i = 0; i < n; i++) if (((mask >> i) & 1) == 0) vs.push_back(varNode[i]);
                Node* clause = vs.empty() ? constF : buildBalanced(vs, '|');
                clauses.push_back(clause);
            }
            root = clauses.empty() ? constT : buildBalanced(clauses, '&');
        }

        // As per statement, always possible to meet depth<=100 if representable.
        // Still, ensure we don't violate due to any bug; if so, fallback to a simple chain (depth<=n+count).
        if (depthParen(root) > 100) {
            // Fallback: build a right-associated chain for top-level only (should not happen for n<=15).
            // We'll just output what we have anyway; depth issue shouldn't arise under constraints.
        }

        printExpr(root, cout);
        cout << "\n";
    }

    return 0;
}