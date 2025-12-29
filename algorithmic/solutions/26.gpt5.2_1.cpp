#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t nextU32() { return (uint32_t)next(); }
};

struct Treap {
    struct Node {
        int val = 0;
        uint32_t pr = 0;
        int sz = 1;
        Node *l = nullptr, *r = nullptr, *p = nullptr;
    };

    int n;
    vector<Node> pool;
    vector<Node*> byVal;
    Node* root = nullptr;
    SplitMix64 rng;

    static inline int sz(Node* t) { return t ? t->sz : 0; }

    static inline void setL(Node* t, Node* c) {
        t->l = c;
        if (c) c->p = t;
    }
    static inline void setR(Node* t, Node* c) {
        t->r = c;
        if (c) c->p = t;
    }
    static inline void pull(Node* t) {
        if (!t) return;
        t->sz = 1 + sz(t->l) + sz(t->r);
    }

    Node* merge(Node* a, Node* b) {
        if (!a) return b;
        if (!b) return a;
        if (a->pr < b->pr) {
            Node* nr = merge(a->r, b);
            setR(a, nr);
            pull(a);
            return a;
        } else {
            Node* nl = merge(a, b->l);
            setL(b, nl);
            pull(b);
            return b;
        }
    }

    pair<Node*, Node*> split(Node* t, int k) { // first k nodes, rest
        if (!t) return {nullptr, nullptr};
        if (sz(t->l) >= k) {
            auto [a, b] = split(t->l, k);
            setL(t, b);
            pull(t);
            if (a) a->p = nullptr;
            t->p = nullptr;
            return {a, t};
        } else {
            auto [a, b] = split(t->r, k - sz(t->l) - 1);
            setR(t, a);
            pull(t);
            t->p = nullptr;
            if (b) b->p = nullptr;
            return {t, b};
        }
    }

    void normalizeRoot() {
        if (root) root->p = nullptr;
    }

    explicit Treap(const vector<int>& v) : n((int)v.size()), pool(n), byVal(n + 1, nullptr) {
        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        seed ^= (uint64_t)(uintptr_t)this + 0x9e3779b97f4a7c15ULL;
        rng = SplitMix64(seed);

        vector<Node*> st;
        st.reserve(n);
        for (int i = 0; i < n; i++) {
            Node* cur = &pool[i];
            cur->val = v[i];
            cur->pr = rng.nextU32();
            cur->sz = 1;
            cur->l = cur->r = cur->p = nullptr;
            byVal[cur->val] = cur;

            Node* last = nullptr;
            while (!st.empty() && st.back()->pr > cur->pr) {
                last = st.back();
                st.pop_back();
            }
            if (last) setL(cur, last);
            if (!st.empty()) setR(st.back(), cur);
            st.push_back(cur);
        }
        root = st.front();
        while (root->p) root = root->p;
        normalizeRoot();

        vector<Node*> order;
        order.reserve(n);
        vector<Node*> dfs;
        dfs.reserve(n);
        dfs.push_back(root);
        while (!dfs.empty()) {
            Node* x = dfs.back();
            dfs.pop_back();
            order.push_back(x);
            if (x->l) dfs.push_back(x->l);
            if (x->r) dfs.push_back(x->r);
        }
        for (int i = (int)order.size() - 1; i >= 0; i--) pull(order[i]);
    }

    int getIndex(Node* x) const { // 1-indexed
        int res = sz(x->l) + 1;
        while (x->p) {
            if (x == x->p->r) res += sz(x->p->l) + 1;
            x = x->p;
        }
        return res;
    }

    void moveIndex(int x, int y) { // move element at position x to position y
        if (x == y) return;
        auto [a, b] = split(root, x - 1);
        auto [mid, c] = split(b, 1);
        root = merge(a, c);
        normalizeRoot();
        auto [d, e] = split(root, y - 1);
        root = merge(merge(d, mid), e);
        normalizeRoot();
    }
};

struct RunResult {
    long long sumY = 0;
    vector<pair<int,int>> ops;
    long long finalCost() const {
        __int128 fc = (__int128)(sumY + 1) * (__int128)((long long)ops.size() + 1);
        return (long long)fc;
    }
};

static RunResult runPrefix(const vector<int>& v) {
    int n = (int)v.size();
    Treap t(v);
    RunResult res;
    res.ops.reserve(n);
    for (int i = 1; i <= n; i++) {
        Treap::Node* nd = t.byVal[i];
        int pos = t.getIndex(nd);
        if (pos == i) continue;
        res.ops.push_back({pos, i});
        res.sumY += i;
        t.moveIndex(pos, i);
    }
    return res;
}

static RunResult runSuffix(const vector<int>& v) {
    int n = (int)v.size();
    Treap t(v);
    RunResult res;
    res.ops.reserve(n);
    for (int i = n; i >= 1; i--) {
        Treap::Node* nd = t.byVal[i];
        int pos = t.getIndex(nd);
        if (pos == i) continue;
        res.ops.push_back({pos, i});
        res.sumY += i;
        t.moveIndex(pos, i);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> v(n);
    for (int i = 0; i < n; i++) cin >> v[i];

    bool sorted = true;
    for (int i = 0; i < n; i++) if (v[i] != i + 1) { sorted = false; break; }

    if (sorted) {
        cout << 1 << " " << 0 << "\n";
        return 0;
    }

    RunResult a = runPrefix(v);
    RunResult b = runSuffix(v);

    long long costA = a.finalCost();
    long long costB = b.finalCost();

    const RunResult* best = &a;
    long long bestCost = costA;
    if (costB < bestCost || (costB == bestCost && b.ops.size() < a.ops.size())) {
        best = &b;
        bestCost = costB;
    }

    cout << bestCost << " " << best->ops.size() << "\n";
    for (auto [x, y] : best->ops) {
        cout << x << " " << y << "\n";
    }
    return 0;
}