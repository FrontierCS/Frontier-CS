#include <bits/stdc++.h>
using namespace std;

struct XorShift {
    uint64_t x;
    XorShift(uint64_t seed=88172645463393265ull) { x = seed; }
    uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    int nextInt(int l, int r) { // inclusive
        return l + (int)(next() % (uint64_t)(r - l + 1));
    }
    double nextDouble() {
        return (next() >> 11) * (1.0/9007199254740992.0);
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if(!(cin >> N >> M)) {
        return 0;
    }
    vector<string> S(M);
    for(int i=0;i<M;i++) cin >> S[i];

    // Compress duplicates with weights
    unordered_map<string, int> freq;
    freq.reserve(M*2);
    for (auto &s: S) ++freq[s];

    struct Item {
        string s;
        int cnt;
        int len;
    };
    vector<Item> items;
    items.reserve(freq.size());
    for (auto &p: freq) items.push_back({p.first, p.second, (int)p.first.size()});
    int U = (int)items.size();

    // Time limit control
    auto start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.8; // seconds

    // RNG
    XorShift rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    auto elapsedSec = [&](){
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(now - start).count();
    };

    // Precompute index vector
    vector<int> idx(U);
    iota(idx.begin(), idx.end(), 0);

    auto cmpDet = [&](int a, int b){
        if (items[a].cnt != items[b].cnt) return items[a].cnt > items[b].cnt;
        if (items[a].len != items[b].len) return items[a].len > items[b].len;
        return items[a].s < items[b].s;
    };

    vector<string> bestGrid(N, string(N, '.'));
    long long bestScore = -1;

    int attempt = 0;
    while (elapsedSec() < TIME_LIMIT) {
        // Prepare order
        if (attempt == 0) {
            sort(idx.begin(), idx.end(), cmpDet);
        } else {
            // Shuffle then stable sort by cnt, len
            shuffle(idx.begin(), idx.end(), std::mt19937(rng.next()));
            stable_sort(idx.begin(), idx.end(), [&](int a, int b){
                if (items[a].cnt != items[b].cnt) return items[a].cnt > items[b].cnt;
                if (items[a].len != items[b].len) return items[a].len > items[b].len;
                return false;
            });
        }

        vector<string> grid(N, string(N, '.'));
        vector<char> placed(U, 0);
        long long score = 0;

        // Try placing each unique string once
        for (int id : idx) {
            const string &t = items[id].s;
            int L = items[id].len;
            int bestDir = -1;
            int bestI = -1, bestJ = -1;
            int bestNew = INT_MAX;

            // Horizontal (dir=0) and Vertical (dir=1)
            // Check all positions
            for (int dir = 0; dir < 2; dir++) {
                for (int i = 0; i < N; i++) {
                    for (int j = 0; j < N; j++) {
                        int add = 0;
                        bool ok = true;
                        for (int p = 0; p < L; p++) {
                            int r = (dir == 0) ? i : (i + p) % N;
                            int c = (dir == 0) ? (j + p) % N : j;
                            char g = grid[r][c];
                            char ch = t[p];
                            if (g == '.') {
                                add++;
                            } else if (g != ch) {
                                ok = false; break;
                            }
                        }
                        if (!ok) continue;
                        if (add < bestNew) {
                            bestNew = add;
                            bestDir = dir;
                            bestI = i; bestJ = j;
                            if (bestNew == 0) goto found_best; // can't improve
                        }
                    }
                }
            }
            found_best:;

            if (bestDir != -1) {
                // Place
                for (int p = 0; p < L; p++) {
                    int r = (bestDir == 0) ? bestI : (bestI + p) % N;
                    int c = (bestDir == 0) ? (bestJ + p) % N : bestJ;
                    grid[r][c] = t[p];
                }
                placed[id] = 1;
                score += items[id].cnt;
            }

            if ((attempt & 3) == 0 && (id & 31) == 0) { // occasional time check
                if (elapsedSec() > TIME_LIMIT) break;
            }
        }

        if (score > bestScore) {
            bestScore = score;
            bestGrid = grid;
        }
        attempt++;
    }

    for (int i = 0; i < N; i++) {
        cout << bestGrid[i] << "\n";
    }
    return 0;
}