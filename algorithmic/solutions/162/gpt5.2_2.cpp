#include <bits/stdc++.h>
using namespace std;

static const int N = 30;
static const int TOTAL = N * (N + 1) / 2;
static const int LIM = 10000;

static inline int idx(int x, int y) { return x * (x + 1) / 2 + y; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> val(TOTAL);
    vector<int> X(TOTAL), Y(TOTAL);
    array<int, 2> parents[TOTAL], children[TOTAL];

    for (int x = 0; x < N; x++) {
        for (int y = 0; y <= x; y++) {
            int v;
            cin >> v;
            val[idx(x, y)] = v;
        }
    }

    for (int x = 0; x < N; x++) {
        for (int y = 0; y <= x; y++) {
            int i = idx(x, y);
            X[i] = x; Y[i] = y;
            parents[i][0] = (x > 0 && y > 0) ? idx(x - 1, y - 1) : -1;
            parents[i][1] = (x > 0 && y < x) ? idx(x - 1, y) : -1;
            children[i][0] = (x < N - 1) ? idx(x + 1, y) : -1;
            children[i][1] = (x < N - 1) ? idx(x + 1, y + 1) : -1;
        }
    }

    vector<array<int, 4>> ops;
    ops.reserve(LIM);

    auto do_swap = [&](int a, int b) -> bool {
        if ((int)ops.size() >= LIM) return false;
        int ax = X[a], ay = Y[a], bx = X[b], by = Y[b];
        ops.push_back({ax, ay, bx, by});
        std::swap(val[a], val[b]);
        return true;
    };

    vector<pair<int,int>> allEdges;
    allEdges.reserve(2 * (TOTAL - N));
    for (int i = 0; i < TOTAL; i++) {
        for (int k = 0; k < 2; k++) {
            int c = children[i][k];
            if (c != -1) allEdges.push_back({i, c});
        }
    }

    auto countViol = [&]() -> int {
        int E = 0;
        for (auto [p, c] : allEdges) if (val[p] > val[c]) E++;
        return E;
    };

    // Priority queue: process deeper parent levels first (larger x).
    // key = (parentX << 20) | code, code = (p << 9) | c.
    priority_queue<long long> pq;
    auto push_edge = [&](int p, int c) {
        if (val[p] <= val[c]) return;
        long long code = ((long long)p << 9) | (long long)c;
        long long key = ((long long)X[p] << 20) | code;
        pq.push(key);
    };

    auto push_incident = [&](int u) {
        for (int k = 0; k < 2; k++) {
            int p = parents[u][k];
            if (p != -1) push_edge(p, u);
        }
        for (int k = 0; k < 2; k++) {
            int c = children[u][k];
            if (c != -1) push_edge(u, c);
        }
    };

    auto run_pq_fix = [&]() {
        while (!pq.empty() && (int)ops.size() < LIM) {
            long long key = pq.top(); pq.pop();
            int code = (int)(key & ((1LL << 20) - 1));
            int p = code >> 9;
            int c = code & 511;
            if (p < 0 || p >= TOTAL || c < 0 || c >= TOTAL) continue;
            if (val[p] <= val[c]) continue;
            if (!do_swap(p, c)) break;
            push_incident(p);
            push_incident(c);
        }
    };

    // Initialize with current violations.
    for (auto [p, c] : allEdges) push_edge(p, c);
    run_pq_fix();

    // Fallback: a few deterministic top-down sift-down passes to clean up remaining violations.
    auto siftDown = [&](int start) -> bool {
        bool changed = false;
        int u = start;
        while ((int)ops.size() < LIM) {
            int c0 = children[u][0], c1 = children[u][1];
            if (c0 == -1 || c1 == -1) break;
            int best = (val[c0] < val[c1]) ? c0 : c1;
            if (val[u] <= val[best]) break;
            if (!do_swap(u, best)) break;
            changed = true;
            u = best;
        }
        return changed;
    };

    if ((int)ops.size() < LIM) {
        for (int pass = 0; pass < 60 && (int)ops.size() < LIM; pass++) {
            bool any = false;
            for (int x = 0; x < N - 1 && (int)ops.size() < LIM; x++) {
                for (int y = 0; y <= x && (int)ops.size() < LIM; y++) {
                    any |= siftDown(idx(x, y));
                }
            }
            if (!any) break;
        }
    }

    // Final rescan using PQ if still violations and we have budget.
    if ((int)ops.size() < LIM) {
        int E = countViol();
        if (E > 0) {
            for (auto [p, c] : allEdges) push_edge(p, c);
            run_pq_fix();
        }
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op[0] << " " << op[1] << " " << op[2] << " " << op[3] << "\n";
    }
    return 0;
}