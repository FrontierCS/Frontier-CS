#include <bits/stdc++.h>
using namespace std;

struct Treap {
    struct Node {
        int val;
        uint32_t pr;
        int sz;
        Node* l;
        Node* r;
        Node(int v, uint32_t p): val(v), pr(p), sz(1), l(nullptr), r(nullptr) {}
    };
    Node* root = nullptr;

    static int sz(Node* t) { return t ? t->sz : 0; }
    static void pull(Node* t) {
        if (t) t->sz = 1 + sz(t->l) + sz(t->r);
    }

    static void split(Node* t, int k, Node*& a, Node*& b) { // first k -> a
        if (!t) { a = b = nullptr; return; }
        int lsz = sz(t->l);
        if (k <= lsz) {
            split(t->l, k, a, t->l);
            pull(t);
            b = t;
        } else {
            split(t->r, k - lsz - 1, t->r, b);
            pull(t);
            a = t;
        }
    }

    static Node* merge(Node* a, Node* b) {
        if (!a || !b) return a ? a : b;
        if (a->pr > b->pr) {
            a->r = merge(a->r, b);
            pull(a);
            return a;
        } else {
            b->l = merge(a, b->l);
            pull(b);
            return b;
        }
    }

    static uint32_t rng() {
        static uint32_t x = 123456789u, y = 362436069u, z = 521288629u, w = 88675123u;
        uint32_t t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }

    void push_back(int v) {
        Node* n = new Node(v, rng());
        root = merge(root, n);
    }

    int getAt(Node* t, int k) const { // 0-index
        while (t) {
            int lsz = sz(t->l);
            if (k < lsz) t = t->l;
            else if (k == lsz) return t->val;
            else { k -= lsz + 1; t = t->r; }
        }
        return -1;
    }
    int getAt(int k) const { return getAt(root, k); }

    void move_pos(int i, int j) { // move element at i to position j
        if (i == j) return;
        if (i > j) {
            Node *A, *B, *B1, *B2, *M, *D;
            split(root, j, A, B);               // A: [0..j-1], B: [j..end]
            split(B, i - j, B1, B2);            // B1: [j..i-1], B2: [i..end]
            split(B2, 1, M, D);                 // M: [i], D: [i+1..]
            root = merge(A, merge(M, merge(B1, D)));
        } else {
            Node *A, *B, *M, *C;
            split(root, i, A, B);               // A: [0..i-1], B: [i..]
            split(B, 1, M, C);                  // M: [i], C: [i+1..]
            Node* rest = merge(A, C);           // remove M
            Node *L, *R;
            split(rest, j - 1, L, R);           // insert at j-1 to end up at j
            root = merge(L, merge(M, R));
        }
    }

    void inorder(Node* t, vector<int>& out) const {
        if (!t) return;
        inorder(t->l, out);
        out.push_back(t->val);
        inorder(t->r, out);
    }
    vector<int> to_vector() const {
        vector<int> out;
        out.reserve(sz(root));
        inorder(root, out);
        return out;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    long long xi, yi;
    for (int i = 0; i < N; ++i) cin >> xi >> yi;

    // Sieve for primes up to N-1
    vector<char> isPrime(max(2, N), true);
    isPrime[0] = false;
    if (N > 1) isPrime[1] = false;
    for (int i = 2; (long long)i * i < N; ++i) {
        if (isPrime[i]) {
            for (int j = i * i; j < N; j += i) isPrime[j] = false;
        }
    }

    Treap treap;
    for (int i = 1; i <= N - 1; ++i) treap.push_back(i);

    int L = N - 1;
    if (L > 0) {
        const int Wf = 120;   // forward search window
        const int Wb = 50;    // backward search window
        auto isSpecialIndex = [](int idx) {
            return ((idx + 2) % 10 == 0);
        };
        for (int j = 8; j < L; j += 10) {
            int vj = treap.getAt(j);
            if (vj >= 0 && isPrime[vj]) continue;

            int found = -1;
            int maxF = min(L - 1, j + Wf);
            for (int i = j + 1; i <= maxF; ++i) {
                int vi = treap.getAt(i);
                if (isPrime[vi]) { found = i; break; }
            }
            if (found != -1) {
                treap.move_pos(found, j);
                continue;
            }

            int minB = max(0, j - Wb);
            for (int i = j - 1; i >= minB; --i) {
                if (isSpecialIndex(i)) continue; // do not disturb earlier special indices
                int vi = treap.getAt(i);
                if (isPrime[vi]) { found = i; break; }
            }
            if (found != -1) {
                treap.move_pos(found, j);
            }
        }
    }

    vector<int> order = treap.to_vector();

    cout << (N + 1) << '\n';
    cout << 0 << '\n';
    for (int v : order) cout << v << '\n';
    cout << 0 << '\n';
    return 0;
}