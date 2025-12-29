#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t x;
    RNG(uint64_t seed = 88172645463325252ull) : x(seed) {}
    uint32_t nextU32() {
        x ^= x << 7;
        x ^= x >> 9;
        return (uint32_t)(x & 0xffffffffu);
    }
};

struct Node {
    int val;
    uint32_t pr;
    Node *l = nullptr, *r = nullptr, *p = nullptr;
    int sz = 1;
};

static inline int sz(Node* t) { return t ? t->sz : 0; }

static inline void pull(Node* t) {
    if (!t) return;
    t->sz = 1 + sz(t->l) + sz(t->r);
    if (t->l) t->l->p = t;
    if (t->r) t->r->p = t;
}

static Node* mergeTreap(Node* a, Node* b) {
    if (!a) { if (b) b->p = nullptr; return b; }
    if (!b) { if (a) a->p = nullptr; return a; }
    if (a->pr < b->pr) {
        a->r = mergeTreap(a->r, b);
        pull(a);
        a->p = nullptr;
        return a;
    } else {
        b->l = mergeTreap(a, b->l);
        pull(b);
        b->p = nullptr;
        return b;
    }
}

static void splitTreap(Node* t, int k, Node*& a, Node*& b) {
    // a: first k nodes, b: rest
    if (!t) { a = b = nullptr; return; }
    if (sz(t->l) >= k) {
        splitTreap(t->l, k, a, t->l);
        pull(t);
        b = t;
        b->p = nullptr;
    } else {
        splitTreap(t->r, k - sz(t->l) - 1, t->r, b);
        pull(t);
        a = t;
        a->p = nullptr;
    }
}

static int getIndex(Node* x) {
    int res = sz(x->l) + 1;
    while (x->p) {
        if (x == x->p->r) res += sz(x->p->l) + 1;
        x = x->p;
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> v(n + 1);
    for (int i = 1; i <= n; i++) cin >> v[i];

    RNG rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<Node> pool(n + 1);
    vector<Node*> ptr(n + 1, nullptr);

    Node* root = nullptr;
    for (int i = 1; i <= n; i++) {
        pool[i].val = v[i];
        pool[i].pr = rng.nextU32();
        pool[i].l = pool[i].r = pool[i].p = nullptr;
        pool[i].sz = 1;
        ptr[v[i]] = &pool[i];
        root = mergeTreap(root, &pool[i]);
    }

    vector<pair<int,int>> ops;
    ops.reserve(n);

    long long totalCost = 0;
    for (int i = 1; i <= n; i++) {
        Node* node = ptr[i];
        int pos = getIndex(node);
        if (pos == i) continue;

        // Remove node at pos
        Node *a, *b, *mid, *c;
        splitTreap(root, pos - 1, a, b);
        splitTreap(b, 1, mid, c);
        root = mergeTreap(a, c);

        // Insert mid at position i
        splitTreap(root, i - 1, a, b);
        root = mergeTreap(mergeTreap(a, mid), b);

        ops.emplace_back(pos, i);
        totalCost += i;
    }

    long long finalCost = (totalCost + 1LL) * ( (long long)ops.size() + 1LL );
    cout << finalCost << ' ' << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << "\n";
    }
    return 0;
}