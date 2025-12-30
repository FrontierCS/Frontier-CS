#include <bits/stdc++.h>
using namespace std;

static inline uint64_t enc(int x, int y) {
    return (uint64_t(x) << 17) | uint64_t(y);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<pair<int,int>> pts(2 * N);
    unordered_set<uint64_t> occ;
    occ.reserve(2 * N * 2);
    occ.max_load_factor(0.7f);

    for (int i = 0; i < 2 * N; i++) {
        int x, y;
        cin >> x >> y;
        pts[i] = {x, y};
        occ.insert(enc(x, y));
    }

    auto emptySquare = [&](int x, int y) -> bool {
        // square corners: (x,y),(x+1,y),(x+1,y+1),(x,y+1)
        return occ.find(enc(x, y)) == occ.end() &&
               occ.find(enc(x + 1, y)) == occ.end() &&
               occ.find(enc(x + 1, y + 1)) == occ.end() &&
               occ.find(enc(x, y + 1)) == occ.end();
    };

    int bestx = -1, besty = -1;

    // Random attempts (very likely to succeed quickly)
    {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        seed ^= (uint64_t)N * 0x9e3779b97f4a7c15ULL;
        mt19937 rng((uint32_t)(seed ^ (seed >> 32)));
        uniform_int_distribution<int> dist(0, 99999);
        for (int t = 0; t < 200000; t++) {
            int x = dist(rng);
            int y = dist(rng);
            if (emptySquare(x, y)) {
                bestx = x;
                besty = y;
                break;
            }
        }
    }

    // Fallback: deterministic scan over a small strip near boundary
    if (bestx < 0) {
        for (int y = 0; y <= 500 && bestx < 0; y++) {
            for (int x = 0; x <= 99999; x++) {
                if (emptySquare(x, y)) {
                    bestx = x;
                    besty = y;
                    break;
                }
            }
        }
    }

    // Last resort: scan entire space (should never be needed)
    if (bestx < 0) {
        for (int y = 0; y <= 99999 && bestx < 0; y++) {
            for (int x = 0; x <= 99999; x++) {
                if (emptySquare(x, y)) {
                    bestx = x;
                    besty = y;
                    break;
                }
            }
        }
    }

    if (bestx < 0) {
        // Extremely unlikely; output a default small square
        bestx = 0; besty = 0;
    }

    cout << 4 << "\n";
    cout << bestx << " " << besty << "\n";
    cout << bestx + 1 << " " << besty << "\n";
    cout << bestx + 1 << " " << besty + 1 << "\n";
    cout << bestx << " " << besty + 1 << "\n";
    return 0;
}