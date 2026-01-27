#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
};

static inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<Order> orders;
    orders.reserve(1000);
    for (int i = 0; i < 1000; ++i) {
        Order o;
        if (!(cin >> o.a >> o.b >> o.c >> o.d)) break;
        orders.push_back(o);
    }
    int N = (int)orders.size();
    if (N == 0) {
        // Fallback: output trivial route with no orders (shouldn't happen in official tests)
        cout << 50;
        for (int i = 0; i < 50; ++i) cout << " " << 1;
        cout << "\n";
        cout << 2 << " " << 400 << " " << 400 << " " << 400 << " " << 400 << "\n";
        return 0;
    }

    const int CX = 400, CY = 400;

    vector<pair<int,int>> score_idx; // (score, idx)
    score_idx.reserve(N);
    for (int i = 0; i < N; ++i) {
        int s = manhattan(CX, CY, orders[i].a, orders[i].b)
              + manhattan(orders[i].a, orders[i].b, orders[i].c, orders[i].d)
              + manhattan(orders[i].c, orders[i].d, CX, CY);
        score_idx.emplace_back(s, i);
    }
    nth_element(score_idx.begin(), score_idx.begin() + min(50, (int)score_idx.size()), score_idx.end());
    sort(score_idx.begin(), score_idx.end());

    int M = 50;
    if (N < 50) M = N; // just in case, though official input has 1000
    vector<int> chosenIndices;
    chosenIndices.reserve(M);
    for (int i = 0; i < M; ++i) {
        chosenIndices.push_back(score_idx[i].second);
    }

    // Build route with greedy nearest neighbor respecting precedence.
    vector<int> ax(M), ay(M), cx(M), cy(M);
    for (int i = 0; i < M; ++i) {
        int idx = chosenIndices[i];
        ax[i] = orders[idx].a; ay[i] = orders[idx].b;
        cx[i] = orders[idx].c; cy[i] = orders[idx].d;
    }

    vector<char> picked(M, 0), delivered(M, 0);
    int deliveredCount = 0;

    vector<pair<int,int>> path;
    path.emplace_back(CX, CY);
    int curx = CX, cury = CY;

    auto process_current = [&](int x, int y) {
        // Pick up all available pickups at current position
        for (int i = 0; i < M; ++i) {
            if (!picked[i] && ax[i] == x && ay[i] == y) picked[i] = 1;
        }
        // Deliver all possible deliveries at current position
        for (int i = 0; i < M; ++i) {
            if (picked[i] && !delivered[i] && cx[i] == x && cy[i] == y) {
                delivered[i] = 1;
                ++deliveredCount;
            }
        }
    };

    process_current(curx, cury);

    while (deliveredCount < M) {
        int bestPickDist = INT_MAX, bestPickIdx = -1;
        int bestDelDist = INT_MAX, bestDelIdx = -1;

        for (int i = 0; i < M; ++i) {
            if (!picked[i]) {
                int d = manhattan(curx, cury, ax[i], ay[i]);
                if (d < bestPickDist) {
                    bestPickDist = d; bestPickIdx = i;
                }
            }
        }
        for (int i = 0; i < M; ++i) {
            if (picked[i] && !delivered[i]) {
                int d = manhattan(curx, cury, cx[i], cy[i]);
                if (d < bestDelDist) {
                    bestDelDist = d; bestDelIdx = i;
                }
            }
        }

        bool goDeliver = false;
        if (bestDelIdx != -1 && (bestDelDist <= bestPickDist || bestPickIdx == -1)) {
            goDeliver = true;
        }

        if (goDeliver) {
            curx = cx[bestDelIdx];
            cury = cy[bestDelIdx];
        } else if (bestPickIdx != -1) {
            curx = ax[bestPickIdx];
            cury = ay[bestPickIdx];
        } else {
            // Should not happen, but to be safe
            break;
        }

        path.emplace_back(curx, cury);
        process_current(curx, cury);
    }

    if (curx != CX || cury != CY) {
        path.emplace_back(CX, CY);
    }

    // Output
    // Ensure exactly 50 orders in output, repeat some if fewer than 50 (unlikely), while keeping distinct indices preferred.
    cout << 50;
    for (int i = 0; i < 50; ++i) {
        int idx = chosenIndices[i % M];
        cout << " " << (idx + 1);
    }
    cout << "\n";

    cout << path.size();
    for (auto &p : path) {
        cout << " " << p.first << " " << p.second;
    }
    cout << "\n";

    return 0;
}