#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    long long L;
    if (!(cin >> N >> L)) return 0;
    vector<long long> T(N);
    for (int i = 0; i < N; i++) cin >> T[i];

    // Initialize a, b
    vector<int> a(N, 0), b(N, 0);

    // Order nodes by T ascending (stable by index)
    vector<int> ord(N);
    iota(ord.begin(), ord.end(), 0);
    stable_sort(ord.begin(), ord.end(), [&](int i, int j){
        if (T[i] != T[j]) return T[i] < T[j];
        return i < j;
    });
    vector<int> pos(N);
    for (int k = 0; k < N; k++) pos[ord[k]] = k;

    // Set b as a single cycle along ord
    for (int k = 0; k < N; k++) {
        int i = ord[k];
        int j = ord[(k+1)%N];
        b[i] = j;
    }

    // Compute deficits D[y] = 2*T[y] - T[pred(y)] to be filled by a-edges
    vector<long long> D(N, 0);
    for (int y = 0; y < N; y++) {
        int k = pos[y];
        int pred = ord[(k - 1 + N) % N];
        D[y] = 2 * T[y] - T[pred];
    }

    // Greedy assign a-edges using a max-heap over deficits
    vector<pair<long long,int>> items;
    items.reserve(N);
    for (int i = 0; i < N; i++) items.emplace_back(T[i], i);
    sort(items.begin(), items.end(), [&](const pair<long long,int>& x, const pair<long long,int>& y){
        if (x.first != y.first) return x.first > y.first;
        return x.second < y.second;
    });

    struct Node { long long val; int y; };
    struct Cmp { bool operator()(const Node& lhs, const Node& rhs) const { return lhs.val < rhs.val; } };
    priority_queue<Node, vector<Node>, Cmp> pq;
    for (int y = 0; y < N; y++) pq.push({D[y], y});

    for (auto &it : items) {
        long long w = it.first;
        int i = it.second;
        // choose y with current maximal D[y]
        Node top;
        while (true) {
            top = pq.top(); pq.pop();
            if (top.val == D[top.y]) break; // valid
        }
        int y = top.y;
        a[i] = y;
        D[y] -= w;
        pq.push({D[y], y});
    }

    // Improvement: minimize sum |R[y]| by reassigning a[i]
    vector<long long> R = D; // residuals after assigning all a-edges
    // Precompute indices for iteration order
    vector<int> idx(N);
    iota(idx.begin(), idx.end(), 0);
    // Deterministic RNG
    std::mt19937 rng(123456789);
    // A few passes of greedy reassignment
    for (int pass = 0; pass < 8; pass++) {
        bool improved = false;
        shuffle(idx.begin(), idx.end(), rng);
        for (int ii = 0; ii < N; ii++) {
            int i = idx[ii];
            int y_old = a[i];
            long long w = T[i];
            if (R[y_old] >= 0) continue; // donor must be overfilled negatively
            long long best_delta = 0;
            int best_y = -1;
            for (int y = 0; y < N; y++) {
                if (y == y_old) continue;
                if (R[y] <= 0) continue; // only move to positive deficit
                long long before = llabs(R[y_old]) + llabs(R[y]);
                long long after = llabs(R[y_old] + w) + llabs(R[y] - w);
                long long delta = after - before;
                if (delta < best_delta) {
                    best_delta = delta;
                    best_y = y;
                }
            }
            if (best_y != -1) {
                // apply move
                R[y_old] += w;
                R[best_y] -= w;
                a[i] = best_y;
                improved = true;
            }
        }
        if (!improved) break;
    }

    // Random pairwise swap improvement
    int SWAPS = 3000;
    uniform_int_distribution<int> distN(0, N-1);
    for (int t = 0; t < SWAPS; t++) {
        int i1 = distN(rng);
        int i2 = distN(rng);
        if (i1 == i2) continue;
        int y1 = a[i1], y2 = a[i2];
        if (y1 == y2) continue;
        long long w1 = T[i1], w2 = T[i2];
        // moving i1 from y1->y2 and i2 from y2->y1
        long long before = llabs(R[y1]) + llabs(R[y2]);
        long long after = llabs(R[y1] + w1 - w2) + llabs(R[y2] + w2 - w1);
        if (after < before) {
            R[y1] = R[y1] + w1 - w2;
            R[y2] = R[y2] + w2 - w1;
            a[i1] = y2;
            a[i2] = y1;
        }
    }

    // Output
    for (int i = 0; i < N; i++) {
        cout << a[i] << " " << b[i] << "\n";
    }
    return 0;
}