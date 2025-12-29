#include <bits/stdc++.h>
using namespace std;

static inline long long ask(int u, int v) {
    printf("? %d %d\n", u, v);
    fflush(stdout);
    long long d;
    if (scanf("%lld", &d) != 1) exit(0);
    if (d < 0) exit(0);
    return d;
}

struct Edge {
    int u, v;
    long long w;
};

struct Task {
    vector<int> nodes;        // nodes[0] is the task root (distance base), but not required for correctness
    vector<long long> dist0;  // dist0[i] = dist(nodes[0], nodes[i])
};

static inline void add_edge(vector<Edge>& edges, int u, int v, long long w) {
    edges.push_back({u, v, w});
}

static inline void process_task(Task&& t, vector<Task>& st, vector<Edge>& edges) {
    int m = (int)t.nodes.size();
    if (m <= 1) return;

    if (m == 2) {
        add_edge(edges, t.nodes[0], t.nodes[1], t.dist0[1]);
        return;
    }

    int root = t.nodes[0];

    // Choose a = farthest from root using known distances dist0
    int idxA = 0;
    for (int i = 1; i < m; i++) {
        if (t.dist0[i] > t.dist0[idxA]) idxA = i;
    }
    int a = t.nodes[idxA];

    // Query distances from a
    vector<long long> dA(m);
    for (int i = 0; i < m; i++) {
        int x = t.nodes[i];
        if (x == a) dA[i] = 0;
        else dA[i] = ask(a, x);
    }

    // b = farthest from a
    int idxB = 0;
    for (int i = 1; i < m; i++) {
        if (dA[i] > dA[idxB]) idxB = i;
    }
    int b = t.nodes[idxB];
    long long D = dA[idxB];

    // Query distances from b (reuse dist0 if b == root)
    vector<long long> dB(m);
    if (b == root) {
        dB = t.dist0;
    } else {
        for (int i = 0; i < m; i++) {
            int x = t.nodes[i];
            if (x == b) dB[i] = 0;
            else dB[i] = ask(b, x);
        }
    }

    // Collect diameter vertices: on path a-b iff dA + dB == D
    vector<pair<long long, int>> diam; // (position from a, vertex)
    diam.reserve(m);
    for (int i = 0; i < m; i++) {
        if (dA[i] + dB[i] == D) {
            diam.push_back({dA[i], t.nodes[i]});
        }
    }
    sort(diam.begin(), diam.end());

    // Connect diameter path
    for (int i = 1; i < (int)diam.size(); i++) {
        add_edge(edges, diam[i - 1].second, diam[i].second, diam[i].first - diam[i - 1].first);
    }

    // Prepare for grouping by projection onto diameter
    int ds = (int)diam.size();
    vector<long long> pos(ds);
    vector<int> dv(ds);
    for (int i = 0; i < ds; i++) {
        pos[i] = diam[i].first;
        dv[i] = diam[i].second;
    }

    vector<vector<int>> groups(ds);
    vector<vector<long long>> groupsDist(ds);

    for (int i = 0; i < m; i++) {
        long long numerator = dA[i] + D - dB[i];
        long long tpos = numerator / 2;
        long long h = dA[i] - tpos;
        if (h == 0) continue; // on diameter

        int idx = (int)(lower_bound(pos.begin(), pos.end(), tpos) - pos.begin());
        // Projection should always be a diameter vertex
        if (idx < 0 || idx >= ds || pos[idx] != tpos) {
            // Fallback: shouldn't happen in a valid tree metric; avoid UB.
            // Put it to the nearest position.
            if (idx == ds) idx = ds - 1;
            else if (idx > 0 && (idx == ds || llabs(pos[idx] - tpos) > llabs(pos[idx - 1] - tpos))) idx--;
        }
        groups[idx].push_back(t.nodes[i]);
        groupsDist[idx].push_back(h);
    }

    // Create child tasks
    for (int i = 0; i < ds; i++) {
        if (groups[i].empty()) continue;
        Task child;
        child.nodes.reserve(1 + groups[i].size());
        child.dist0.reserve(1 + groups[i].size());
        child.nodes.push_back(dv[i]);
        child.dist0.push_back(0);
        for (size_t j = 0; j < groups[i].size(); j++) {
            child.nodes.push_back(groups[i][j]);
            child.dist0.push_back(groupsDist[i][j]); // dist(dv[i], node)
        }
        st.push_back(std::move(child));
    }
}

int main() {
    int T;
    if (scanf("%d", &T) != 1) return 0;

    while (T--) {
        int n;
        if (scanf("%d", &n) != 1) return 0;

        if (n <= 1) {
            printf("!\n");
            fflush(stdout);
            continue;
        }

        vector<Edge> edges;
        edges.reserve(n - 1);

        Task initial;
        initial.nodes.resize(n);
        initial.dist0.resize(n);
        for (int i = 0; i < n; i++) initial.nodes[i] = i + 1;
        initial.dist0[0] = 0;
        for (int i = 2; i <= n; i++) {
            initial.dist0[i - 1] = ask(1, i);
        }

        vector<Task> st;
        st.reserve(n);
        st.push_back(std::move(initial));

        while (!st.empty()) {
            Task t = std::move(st.back());
            st.pop_back();
            process_task(std::move(t), st, edges);
        }

        // Output answer
        printf("!");
        for (auto &e : edges) {
            printf(" %d %d %lld", e.u, e.v, e.w);
        }
        printf("\n");
        fflush(stdout);
    }

    return 0;
}