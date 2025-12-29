#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() {
#ifdef _WIN32
        return getchar();
#else
        return getchar_unlocked();
#endif
    }
    template <class T>
    bool readInt(T &out) {
        int c;
        do {
            c = gc();
            if (c == EOF) return false;
        } while (c <= ' ');

        T sign = 1;
        if (c == '-') { sign = -1; c = gc(); }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = gc();
        }
        out = val * sign;
        return true;
    }
};

static uint64_t splitmix64_state = chrono::steady_clock::now().time_since_epoch().count();
static inline uint64_t splitmix64() {
    uint64_t z = (splitmix64_state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct Node {
    int val;
    uint32_t prio;
    int sz;
    Node *l, *r, *p;
    Node(int v) : val(v), prio((uint32_t)splitmix64()), sz(1), l(nullptr), r(nullptr), p(nullptr) {}
};

static inline int sz(Node* t) { return t ? t->sz : 0; }

static inline void pull(Node* t) {
    if (!t) return;
    t->sz = 1 + sz(t->l) + sz(t->r);
    if (t->l) t->l->p = t;
    if (t->r) t->r->p = t;
}

static void split(Node* t, int k, Node* &a, Node* &b) { // first k nodes -> a
    if (!t) { a = b = nullptr; return; }
    if (sz(t->l) >= k) {
        split(t->l, k, a, t->l);
        if (t->l) t->l->p = t;
        b = t;
        b->p = nullptr;
        pull(b);
    } else {
        split(t->r, k - sz(t->l) - 1, t->r, b);
        if (t->r) t->r->p = t;
        a = t;
        a->p = nullptr;
        pull(a);
    }
}

static Node* merge(Node* a, Node* b) {
    if (!a) { if (b) b->p = nullptr; return b; }
    if (!b) { if (a) a->p = nullptr; return a; }
    if (a->prio < b->prio) {
        a->r = merge(a->r, b);
        if (a->r) a->r->p = a;
        pull(a);
        a->p = nullptr;
        return a;
    } else {
        b->l = merge(a, b->l);
        if (b->l) b->l->p = b;
        pull(b);
        b->p = nullptr;
        return b;
    }
}

static inline int indexOf(Node* t) {
    int res = sz(t->l) + 1;
    while (t->p) {
        if (t == t->p->r) res += sz(t->p->l) + 1;
        t = t->p;
    }
    return res;
}

static inline void moveToFront(Node* &root, int x) { // move position x to position 1
    Node *a, *b, *mid, *c;
    split(root, x - 1, a, b);
    split(b, 1, mid, c);
    root = merge(mid, merge(a, c));
    if (root) root->p = nullptr;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    if (!fs.readInt(n)) return 0;

    vector<int> v(n + 1), pos(n + 1);
    vector<Node*> nodeOf(n + 1, nullptr);

    Node* root = nullptr;
    for (int i = 1; i <= n; i++) {
        fs.readInt(v[i]);
        pos[v[i]] = i;
        Node* nd = new Node(v[i]);
        nodeOf[v[i]] = nd;
        root = merge(root, nd);
    }
    if (root) root->p = nullptr;

    int t = n;
    for (int i = n - 1; i >= 1; i--) {
        if (pos[i] < pos[i + 1]) t = i;
        else break;
    }

    int m = t - 1;
    long long final_cost = 1LL * (m + 1) * (m + 1);

    cout << final_cost << ' ' << m << '\n';
    for (int val = t - 1; val >= 1; val--) {
        Node* nd = nodeOf[val];
        int x = indexOf(nd);
        cout << x << ' ' << 1 << '\n';
        moveToFront(root, x);
    }

    return 0;
}