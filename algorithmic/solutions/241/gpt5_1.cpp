#include <bits/stdc++.h>
using namespace std;

struct Node {
    char type; // 'V' variable, 'T', 'F', 'A' AND, 'O' OR
    int left = -1, right = -1;
    int var = -1; // for 'V'
};

static inline int popcntu(unsigned x){ return __builtin_popcount(x); }

bool isMonotone(const string &s, int n) {
    unsigned L = 1u << n;
    for (int i = 0; i < n; ++i) {
        unsigned step = 1u << i;
        for (unsigned base = 0; base < L; base += (step << 1)) {
            for (unsigned off = 0; off < step; ++off) {
                unsigned a = base + off;
                unsigned b = a + step;
                if (s[a] == '1' && s[b] == '0') return false;
            }
        }
    }
    return true;
}

vector<unsigned> minimalOnes(const string &s, int n) {
    unsigned L = 1u << n;
    vector<unsigned> res;
    for (unsigned m = 0; m < L; ++m) if (s[m] == '1') {
        unsigned mm = m;
        bool ok = true;
        while (mm) {
            unsigned b = mm & -mm;
            if (s[m ^ b] == '1') { ok = false; break; }
            mm ^= b;
        }
        if (ok) res.push_back(m);
    }
    return res;
}

vector<unsigned> maximalZeros(const string &s, int n) {
    unsigned L = 1u << n;
    unsigned full = L - 1;
    vector<unsigned> res;
    for (unsigned m = 0; m < L; ++m) if (s[m] == '0') {
        unsigned mm = (~m) & full;
        bool ok = true;
        while (mm) {
            unsigned b = mm & -mm;
            if (s[m | b] == '0') { ok = false; break; }
            mm ^= b;
        }
        if (ok) res.push_back(m);
    }
    return res;
}

int joinBalanced(vector<int> items, char op, vector<Node> &nodes) {
    if (items.empty()) return -1;
    if (items.size() == 1) return items[0];
    vector<int> cur = std::move(items);
    while (cur.size() > 1) {
        vector<int> nxt;
        nxt.reserve((cur.size()+1)/2);
        for (size_t i = 0; i < cur.size(); i += 2) {
            if (i + 1 < cur.size()) {
                Node nd; nd.type = op; nd.left = cur[i]; nd.right = cur[i+1];
                nodes.push_back(nd);
                nxt.push_back((int)nodes.size()-1);
            } else {
                nxt.push_back(cur[i]);
            }
        }
        cur.swap(nxt);
    }
    return cur[0];
}

void printNode(int idx, const vector<Node> &nodes, ostream &os) {
    const Node &nd = nodes[idx];
    if (nd.type == 'V') {
        os << char('a' + nd.var);
    } else if (nd.type == 'T') {
        os << 'T';
    } else if (nd.type == 'F') {
        os << 'F';
    } else {
        os << '(';
        printNode(nd.left, nodes, os);
        os << (nd.type == 'A' ? '&' : '|');
        printNode(nd.right, nodes, os);
        os << ')';
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
        unsigned L = 1u << n;
        if (s.size() != L) {
            cout << "No\n";
            continue;
        }
        if (!isMonotone(s, n)) {
            cout << "No\n";
            continue;
        }
        // Constants
        if (s[0] == '1') {
            cout << "Yes\n";
            cout << "T\n";
            continue;
        }
        if (s[L-1] == '0') {
            cout << "Yes\n";
            cout << "F\n";
            continue;
        }

        // Compute minimal ones and maximal zeros
        vector<unsigned> mins = minimalOnes(s, n);
        vector<unsigned> maxs = maximalZeros(s, n);

        // Compute operator counts for DNF and CNF
        long long opsDNF = 0, opsCNF = 0;
        long long t = (long long)mins.size();
        long long c = (long long)maxs.size();
        long long sumAnd = 0;
        for (unsigned m : mins) {
            int k = popcntu(m);
            if (k >= 1) sumAnd += (k - 1);
        }
        if (t >= 1) opsDNF = sumAnd + (t - 1);
        long long sumOr = 0;
        for (unsigned m : maxs) {
            int k = n - popcntu(m);
            if (k >= 1) sumOr += (k - 1);
        }
        if (c >= 1) opsCNF = sumOr + (c - 1);

        bool useDNF = (opsDNF <= opsCNF);

        // Build expression tree
        vector<Node> nodes;
        nodes.reserve((size_t)(n + 2 + max(opsDNF, opsCNF) + 8));
        // Create variable leaves
        vector<int> varLeaf(n);
        for (int i = 0; i < n; ++i) {
            Node v; v.type = 'V'; v.var = i;
            nodes.push_back(v);
            varLeaf[i] = (int)nodes.size()-1;
        }
        // Constants (not used inside typical joins here, but keep for completeness)
        int idxT = -1, idxF = -1;
        {
            Node tN; tN.type = 'T'; nodes.push_back(tN); idxT = (int)nodes.size()-1;
            Node fN; fN.type = 'F'; nodes.push_back(fN); idxF = (int)nodes.size()-1;
        }

        int root = -1;
        if (useDNF) {
            vector<int> terms;
            terms.reserve(mins.size());
            for (unsigned m : mins) {
                vector<int> vars;
                vars.reserve(popcntu(m));
                unsigned mm = m;
                while (mm) {
                    unsigned b = mm & -mm;
                    int i = __builtin_ctz(b);
                    vars.push_back(varLeaf[i]);
                    mm ^= b;
                }
                if (vars.empty()) {
                    terms.push_back(idxT);
                } else if ((int)vars.size() == 1) {
                    terms.push_back(vars[0]);
                } else {
                    int conj = joinBalanced(vars, 'A', nodes);
                    terms.push_back(conj);
                }
            }
            if (terms.empty()) {
                root = idxF;
            } else if (terms.size() == 1) {
                root = terms[0];
            } else {
                root = joinBalanced(terms, 'O', nodes);
            }
        } else {
            vector<int> clauses;
            clauses.reserve(maxs.size());
            unsigned full = (1u << n) - 1;
            for (unsigned m : maxs) {
                vector<int> vars;
                unsigned mm = (~m) & full;
                vars.reserve(n - popcntu(m));
                while (mm) {
                    unsigned b = mm & -mm;
                    int i = __builtin_ctz(b);
                    vars.push_back(varLeaf[i]);
                    mm ^= b;
                }
                if (vars.empty()) {
                    clauses.push_back(idxF);
                } else if ((int)vars.size() == 1) {
                    clauses.push_back(vars[0]);
                } else {
                    int clause = joinBalanced(vars, 'O', nodes);
                    clauses.push_back(clause);
                }
            }
            if (clauses.empty()) {
                root = idxT;
            } else if (clauses.size() == 1) {
                root = clauses[0];
            } else {
                root = joinBalanced(clauses, 'A', nodes);
            }
        }

        cout << "Yes\n";
        if (root == -1) {
            // Shouldn't happen; fallback
            cout << "F\n";
        } else {
            printNode(root, nodes, cout);
            cout << "\n";
        }
    }
    return 0;
}