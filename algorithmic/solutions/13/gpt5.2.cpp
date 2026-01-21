#include <bits/stdc++.h>
using namespace std;

static const int T = 3000;

static inline uint64_t keyCell(int x, int y) {
    return (uint64_t)(uint32_t)x << 32 | (uint32_t)y;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int rx, ry;
    if (!(cin >> rx >> ry)) return 0;

    unordered_set<uint64_t> black;
    black.reserve(10000);

    int prx = -1, pry = -1;

    auto isBlack = [&](int x, int y) -> bool {
        if (x < 1 || y < 1) return false;
        return black.find(keyCell(x, y)) != black.end();
    };

    auto neighbors = [&](int x, int y) {
        vector<pair<int,int>> nb;
        for (int dx = -1; dx <= 1; dx++) {
            for (int dy = -1; dy <= 1; dy++) {
                if (dx == 0 && dy == 0) continue;
                int nx = x + dx, ny = y + dy;
                if (nx > 0 && ny > 0) nb.push_back({nx, ny});
            }
        }
        return nb;
    };

    auto safeMoves = [&](int x, int y, const unordered_set<uint64_t>& blk) {
        vector<pair<int,int>> mv;
        for (int dx = -1; dx <= 1; dx++) {
            for (int dy = -1; dy <= 1; dy++) {
                if (dx == 0 && dy == 0) continue;
                int nx = x + dx, ny = y + dy;
                if (nx <= 0 || ny <= 0) continue;
                if (blk.find(keyCell(nx, ny)) == blk.end()) mv.push_back({nx, ny});
            }
        }
        return mv;
    };

    auto heur = [&](int x, int y, const unordered_set<uint64_t>& blk) -> long long {
        // Smaller is better.
        // Encourage closeness to origin and fewer safe moves / more mined neighbors.
        long long dist = (long long)x + (long long)y;
        int minedAdj = 0, safeAdj = 0;
        for (int dx = -1; dx <= 1; dx++) {
            for (int dy = -1; dy <= 1; dy++) {
                if (dx == 0 && dy == 0) continue;
                int nx = x + dx, ny = y + dy;
                if (nx <= 0 || ny <= 0) continue;
                if (blk.find(keyCell(nx, ny)) != blk.end()) minedAdj++;
                else safeAdj++;
            }
        }
        // Penalize being far from origin; reward having many mined neighbors; penalize many safe options.
        long long score = dist * 1000LL + (long long)safeAdj * 500LL - (long long)minedAdj * 200LL;

        // Slightly encourage staying within marking range.
        if (x > T || y > T) score += 100000000LL;
        else score += (long long)(x + y) * 2LL;

        // Prefer smaller coordinates overall to keep game manageable.
        score += (long long)max(x, y) * 5LL;
        return score;
    };

    for (int turn = 1; turn <= T; turn++) {
        vector<pair<int,int>> cand;

        auto addCand = [&](int x, int y) {
            if (x < 1 || y < 1 || x > T || y > T) return;
            cand.push_back({x, y});
        };

        // Primary candidates: neighbors of current position.
        for (int dx = -1; dx <= 1; dx++) {
            for (int dy = -1; dy <= 1; dy++) {
                if (dx == 0 && dy == 0) continue;
                addCand(rx + dx, ry + dy);
            }
        }

        // Also include current cell (to discourage revisits), and previous cell.
        addCand(rx, ry);
        if (prx != -1) addCand(prx, pry);

        // Add a few 2-step candidates to shape the space.
        for (int dx = -2; dx <= 2; dx++) {
            for (int dy = -2; dy <= 2; dy++) {
                if (abs(dx) + abs(dy) != 2) continue;
                addCand(rx + dx, ry + dy);
            }
        }

        // Add some deterministic "net" points near origin (occasionally helpful).
        // Choose a point depending on turn; keep within [1..T].
        {
            int a = (turn * 37) % T + 1;
            int b = (turn * 91) % T + 1;
            addCand(a, 1);
            addCand(1, b);
            addCand(a, b);
        }

        // Deduplicate candidates.
        sort(cand.begin(), cand.end());
        cand.erase(unique(cand.begin(), cand.end()), cand.end());

        pair<int,int> best = {1, 1};
        int bestSafeCnt = INT_MAX;
        long long bestWorstHeur = (1LL << 62);
        bool bestIsNew = false;

        for (auto [mx, my] : cand) {
            unordered_set<uint64_t> blk = black;
            uint64_t k = keyCell(mx, my);
            blk.insert(k);

            auto mv = safeMoves(rx, ry, blk);
            int safeCnt = (int)mv.size();

            if (safeCnt == 0) {
                best = {mx, my};
                bestSafeCnt = 0;
                bestWorstHeur = LLONG_MIN;
                bestIsNew = (black.find(k) == black.end());
                break;
            }

            long long worst = LLONG_MIN;
            for (auto [nx, ny] : mv) {
                long long h = heur(nx, ny, blk);
                worst = max(worst, h);
            }

            bool isNew = (black.find(k) == black.end());

            // Lexicographic: minimize safeCnt, then minimize worst heuristic, then prefer new cell.
            if (safeCnt < bestSafeCnt ||
                (safeCnt == bestSafeCnt && (worst < bestWorstHeur ||
                 (worst == bestWorstHeur && isNew && !bestIsNew)))) {
                bestSafeCnt = safeCnt;
                bestWorstHeur = worst;
                best = {mx, my};
                bestIsNew = isNew;
            }
        }

        // Ensure best is within bounds.
        if (best.first < 1 || best.second < 1 || best.first > T || best.second > T) best = {1, 1};

        // Play.
        cout << best.first << ' ' << best.second << "\n";
        cout.flush();

        black.insert(keyCell(best.first, best.second));

        // Read robot response.
        int nx, ny;
        if (!(cin >> nx >> ny)) break;
        if (nx == 0 && ny == 0) break;

        prx = rx; pry = ry;
        rx = nx; ry = ny;
    }

    return 0;
}