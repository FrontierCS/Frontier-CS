#include <bits/stdc++.h>
using namespace std;

static long long queryCount = 0;

static long long ask_set(const vector<int>& nodes) {
    cout << "? 1 " << nodes.size();
    for (int u : nodes) cout << " " << u;
    cout << "\n" << flush;
    long long res;
    if (!(cin >> res)) exit(0);
    ++queryCount;
    return res;
}

static long long ask_single(int u) {
    cout << "? 1 1 " << u << "\n" << flush;
    long long res;
    if (!(cin >> res)) exit(0);
    ++queryCount;
    return res;
}

static void toggle_node(int u) {
    cout << "? 2 " << u << "\n" << flush;
    ++queryCount;
}

static long long descendant_count_in_set(int c, const vector<int>& nodes) {
    if (nodes.empty()) return 0;
    long long a = ask_set(nodes);
    toggle_node(c);
    long long b = ask_set(nodes);
    long long d = llabs(b - a);
    return d / 2;
}

static int find_centroid(const vector<vector<int>>& adj, const vector<int>& candNodes, const vector<char>& inCand) {
    int n = (int)adj.size() - 1;
    int root = candNodes[0];

    vector<int> parent(n + 1, -1);
    vector<int> order;
    order.reserve(candNodes.size());

    stack<int> st;
    st.push(root);
    parent[root] = 0;

    while (!st.empty()) {
        int u = st.top();
        st.pop();
        order.push_back(u);
        for (int v : adj[u]) {
            if (!inCand[v] || v == parent[u]) continue;
            parent[v] = u;
            st.push(v);
        }
    }

    vector<int> sz(n + 1, 0);
    for (int i = (int)order.size() - 1; i >= 0; --i) {
        int u = order[i];
        int s = 1;
        for (int v : adj[u]) {
            if (!inCand[v] || parent[v] != u) continue;
            s += sz[v];
        }
        sz[u] = s;
    }

    int total = (int)candNodes.size();
    int bestNode = root;
    int bestMaxPart = total + 1;

    for (int u : candNodes) {
        int mx = total - sz[u];
        for (int v : adj[u]) {
            if (!inCand[v] || parent[v] != u) continue;
            mx = max(mx, sz[v]);
        }
        if (mx < bestMaxPart) {
            bestMaxPart = mx;
            bestNode = u;
        }
    }

    return bestNode;
}

static vector<int> collect_component(const vector<vector<int>>& adj, int start, int banned, const vector<char>& inCand) {
    vector<int> comp;
    stack<pair<int,int>> st;
    st.push({start, banned});
    while (!st.empty()) {
        auto [u, p] = st.top();
        st.pop();
        comp.push_back(u);
        for (int v : adj[u]) {
            if (!inCand[v] || v == p || v == banned) continue;
            st.push({v, u});
        }
    }
    return comp;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        queryCount = 0;

        vector<int> candNodes;
        candNodes.reserve(n);
        vector<char> inCand(n + 1, false);
        for (int i = 1; i <= n; i++) {
            candNodes.push_back(i);
            inCand[i] = true;
        }

        int root = -1;

        while (true) {
            if (candNodes.size() == 1) {
                root = candNodes[0];
                break;
            }

            int c = find_centroid(adj, candNodes, inCand);

            vector<int> S;
            S.reserve(candNodes.size() - 1);
            for (int u : candNodes) if (u != c) S.push_back(u);

            if (S.empty()) {
                root = c;
                break;
            }

            long long descAll = descendant_count_in_set(c, S);
            if (descAll == (long long)S.size()) {
                root = c;
                break;
            }

            int sizeA = (int)((long long)S.size() - descAll); // size of root component in cand after removing c

            vector<vector<int>> comps;
            comps.reserve(adj[c].size());
            for (int v : adj[c]) {
                if (!inCand[v]) continue;
                comps.push_back(collect_component(adj, v, c, inCand));
            }

            vector<int> ids;
            for (int i = 0; i < (int)comps.size(); i++) {
                if ((int)comps[i].size() == sizeA) ids.push_back(i);
            }
            if (ids.empty()) {
                // Shouldn't happen; fallback to keep searching with a direct test over each component
                // (still bounded by n<=1000).
                for (int i = 0; i < (int)comps.size(); i++) {
                    long long d = descendant_count_in_set(c, comps[i]);
                    if (d == 0) {
                        ids = {i};
                        break;
                    }
                }
                if (ids.empty()) ids = {0};
            }

            while (ids.size() > 1) {
                int half = (int)ids.size() / 2;
                vector<int> uni;
                int uniSz = 0;
                for (int i = 0; i < half; i++) uniSz += (int)comps[ids[i]].size();
                uni.reserve(uniSz);
                for (int i = 0; i < half; i++) {
                    const auto& vec = comps[ids[i]];
                    uni.insert(uni.end(), vec.begin(), vec.end());
                }

                long long d = descendant_count_in_set(c, uni);
                if (d < (long long)uni.size()) {
                    ids.resize(half);
                } else {
                    ids.erase(ids.begin(), ids.begin() + half);
                }
            }

            vector<int> nextCand = comps[ids[0]];
            fill(inCand.begin(), inCand.end(), false);
            for (int u : nextCand) inCand[u] = true;
            candNodes.swap(nextCand);
        }

        vector<long long> f(n + 1, 0);
        for (int i = 1; i <= n; i++) f[i] = ask_single(i);

        vector<int> parent(n + 1, -1);
        queue<int> q;
        parent[root] = 0;
        q.push(root);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (v == parent[u]) continue;
                if (parent[v] != -1) continue;
                parent[v] = u;
                q.push(v);
            }
        }

        vector<int> val(n + 1, 1);
        val[root] = (int)f[root];
        for (int i = 1; i <= n; i++) {
            if (i == root) continue;
            val[i] = (int)(f[i] - f[parent[i]]);
        }

        cout << "!";
        for (int i = 1; i <= n; i++) cout << " " << val[i];
        cout << "\n" << flush;
    }

    return 0;
}