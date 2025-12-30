#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXN = 100;

struct PlanResult {
    long long err = (1LL<<62);
    array<int, MAXN> cnt{};
};

static inline PlanResult simulate_plan(int N, int L, const array<int, MAXN>& T,
                                       const array<int, MAXN>& a, const array<int, MAXN>& b) {
    PlanResult res;
    res.cnt.fill(0);
    int cur = 0;
    for (int w = 0; w < L; w++) {
        int &c = res.cnt[cur];
        c++;
        int nxt = (c & 1) ? a[cur] : b[cur];
        cur = nxt;
    }
    long long e = 0;
    for (int i = 0; i < N; i++) e += llabs((long long)res.cnt[i] - (long long)T[i]);
    res.err = e;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, L;
    cin >> N >> L;
    array<int, MAXN> T{};
    for (int i = 0; i < N; i++) cin >> T[i];

    array<int, MAXN> a{}, b{};
    for (int i = 0; i < N; i++) a[i] = b[i] = i;

    vector<int> active;
    active.reserve(N);
    for (int i = 0; i < N; i++) if (T[i] > 0) active.push_back(i);
    if (find(active.begin(), active.end(), 0) == active.end()) active.push_back(0);

    if ((int)active.size() == 1) {
        for (int i = 0; i < N; i++) {
            cout << i << " " << i << "\n";
        }
        return 0;
    }

    // Build a base cycle on active nodes, with 0 first, others by descending T.
    vector<int> others;
    others.reserve(active.size());
    for (int v : active) if (v != 0) others.push_back(v);
    sort(others.begin(), others.end(), [&](int x, int y){
        if (T[x] != T[y]) return T[x] > T[y];
        return x < y;
    });

    vector<int> order;
    order.reserve(active.size());
    order.push_back(0);
    for (int v : others) order.push_back(v);

    int m = (int)order.size();
    vector<int> pos(N, -1);
    for (int i = 0; i < m; i++) pos[order[i]] = i;

    // Fix a-edges to ensure reachability: a[order[i]] = order[(i+1)%m]
    for (int i = 0; i < m; i++) {
        int u = order[i];
        int v = order[(i + 1) % m];
        a[u] = v;
    }

    // Remaining demand for each node after assigning all a-edges:
    // Demand is 2*T[j] total incoming flow, and a-edge from i contributes T[i] to a[i].
    vector<long long> D(N, 0);
    for (int i = 0; i < N; i++) D[i] = 2LL * T[i];
    for (int i = 0; i < m; i++) {
        int u = order[i];
        int v = a[u];
        D[v] -= (long long)T[u];
    }

    // Only allow destinations within active set; inactive nodes remain isolated.
    vector<int> act = order; // active in a stable order
    vector<char> is_active(N, 0);
    for (int v : act) is_active[v] = 1;

    // Greedy assignment for b edges to satisfy remaining demand.
    priority_queue<pair<long long,int>> pq;
    for (int v : act) pq.push({D[v], v});

    for (int u : act) {
        auto [rem, v] = pq.top();
        pq.pop();
        b[u] = v;
        rem -= (long long)T[u];
        pq.push({rem, v});
    }

    // Randomized hill-climb on b edges (a edges kept as cycle).
    mt19937 rng(0xC0FFEE);
    auto rand_int = [&](int l, int r)->int{
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    };

    PlanResult best = simulate_plan(N, L, T, a, b);
    PlanResult curRes = best;

    // Prepare active list for random selection
    vector<int> actNodes = act;

    const int ITER = 70;
    for (int it = 0; it < ITER; it++) {
        // Build top deficit nodes (want more visits)
        vector<pair<int,int>> deficit; deficit.reserve(actNodes.size());
        for (int v : actNodes) {
            int d = T[v] - curRes.cnt[v];
            deficit.push_back({d, v});
        }
        sort(deficit.begin(), deficit.end(), [&](auto &p1, auto &p2){
            if (p1.first != p2.first) return p1.first > p2.first;
            return p1.second < p2.second;
        });

        int u = actNodes[rand_int(0, (int)actNodes.size() - 1)];
        int oldv = b[u];

        int newv;
        int roll = rand_int(0, 99);
        if (roll < 75) {
            int K = min<int>(10, deficit.size());
            vector<int> cand;
            cand.reserve(K);
            for (int i = 0; i < K; i++) {
                if (deficit[i].first <= 0) break;
                cand.push_back(deficit[i].second);
            }
            if (!cand.empty()) newv = cand[rand_int(0, (int)cand.size() - 1)];
            else newv = actNodes[rand_int(0, (int)actNodes.size() - 1)];
        } else {
            newv = actNodes[rand_int(0, (int)actNodes.size() - 1)];
        }

        if (newv == oldv) continue;
        b[u] = newv;

        PlanResult nextRes = simulate_plan(N, L, T, a, b);
        if (nextRes.err <= curRes.err) {
            curRes = nextRes;
            if (curRes.err < best.err) best = curRes;
        } else {
            b[u] = oldv;
        }
    }

    // Output final plan
    for (int i = 0; i < N; i++) {
        int ai = a[i], bi = b[i];
        if (ai < 0 || ai >= N) ai = i;
        if (bi < 0 || bi >= N) bi = i;
        cout << ai << " " << bi << "\n";
    }
    return 0;
}