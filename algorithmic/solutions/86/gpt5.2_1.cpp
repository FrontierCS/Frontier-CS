#include <bits/stdc++.h>
using namespace std;

static int n;
static int queryCount = 0;
static const int QUERY_LIMIT = 20000;

static vector<vector<int>> lca_cache; // lca with root=1, 0 = unknown
static vector<int> parent_;
static vector<vector<int>> children_;
static vector<char> inserted;

static int ask(int a, int b, int c) {
    if (queryCount >= QUERY_LIMIT) {
        // In a real interactive environment, exceeding would likely result in -1.
        // Exit to avoid undefined behavior.
        exit(0);
    }
    cout << 0 << ' ' << a << ' ' << b << ' ' << c << '\n';
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    ++queryCount;
    return res;
}

static int lca1(int u, int v) {
    if (u == v) return u;
    if (u == 1 || v == 1) return 1;
    int &ref = lca_cache[u][v];
    if (ref) return ref;
    int ans = ask(1, u, v);
    lca_cache[u][v] = ans;
    lca_cache[v][u] = ans;
    return ans;
}

static bool is_ancestor(int u, int v) {
    if (u == v) return true;
    if (u == 1) return true;
    if (v == 1) return false;
    return lca1(u, v) == u;
}

static int find_parent_for(int v) {
    int cur = 1;
    while (true) {
        int nxt = -1;
        for (int c : children_[cur]) {
            if (is_ancestor(c, v)) {
                nxt = c;
                break;
            }
        }
        if (nxt == -1) return cur;
        cur = nxt;
    }
}

static void insert_node(int v) {
    int p = find_parent_for(v);
    parent_[v] = p;
    children_[p].push_back(v);
    inserted[v] = 1;

    // Reattach children of p that are descendants of v
    auto &vec = children_[p];
    for (int i = 0; i < (int)vec.size();) {
        int c = vec[i];
        if (c == v) {
            ++i;
            continue;
        }
        if (is_ancestor(v, c)) {
            vec[i] = vec.back();
            vec.pop_back();
            children_[v].push_back(c);
            parent_[c] = v;
        } else {
            ++i;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;

    lca_cache.assign(n + 1, vector<int>(n + 1, 0));
    parent_.assign(n + 1, 0);
    children_.assign(n + 1, {});
    inserted.assign(n + 1, 0);

    inserted[1] = 1;
    parent_[1] = 0;

    vector<int> order;
    order.reserve(n - 1);
    for (int i = 2; i <= n; i++) order.push_back(i);

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    shuffle(order.begin(), order.end(), rng);

    for (int v : order) insert_node(v);

    cout << 1;
    for (int v = 2; v <= n; v++) {
        cout << ' ' << parent_[v] << ' ' << v;
    }
    cout << '\n';
    cout.flush();
    return 0;
}