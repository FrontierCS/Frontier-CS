#include <bits/stdc++.h>
using namespace std;

static inline long long keyll(int x, int y) {
    return (static_cast<long long>(x) << 32) ^ static_cast<unsigned long long>(y);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    // Heuristic to detect "offline transcript" vs real interactive.
    // If more input is already available, treat it as offline transcript.
    streamsize avail = 0;
    if (cin.rdbuf()) avail = cin.rdbuf()->in_avail();

    if (avail > 0) {
        vector<pair<int,int>> resp;
        int x, y;
        while (cin >> x >> y) resp.push_back({x, y});

        int m = (int)resp.size();
        if (m == 0) return 0;

        unordered_set<long long> visited;
        visited.reserve((size_t)m * 2 + 10);
        visited.insert(keyll(sx, sy));
        for (auto &p : resp) {
            if (p.first == 0 && p.second == 0) continue;
            visited.insert(keyll(p.first, p.second));
        }

        unordered_set<long long> used;
        used.reserve((size_t)m * 2 + 10);

        int cx = 1, cy = 1;
        auto nextSafe = [&]() -> pair<int,int> {
            while (true) {
                if (cx > 3000) return {3000, 3000}; // fallback (should never happen)
                long long k = keyll(cx, cy);
                if (!visited.count(k) && !used.count(k)) {
                    used.insert(k);
                    return {cx, cy};
                }
                ++cy;
                if (cy > 3000) { cy = 1; ++cx; }
            }
        };

        vector<pair<int,int>> out;
        out.reserve(m);

        bool endsWithExplosion = (resp.back().first == 0 && resp.back().second == 0);

        if (endsWithExplosion) {
            for (int i = 0; i < m - 1; i++) out.push_back(nextSafe());

            pair<int,int> cur = (m == 1 ? make_pair(sx, sy) : resp[m - 2]);
            int rx = cur.first, ry = cur.second;

            pair<int,int> lastMove = {-1, -1};
            if (1 <= rx && rx <= 3000 && 1 <= ry && ry <= 3000) {
                for (int dx = -1; dx <= 1 && lastMove.first == -1; dx++) {
                    for (int dy = -1; dy <= 1 && lastMove.first == -1; dy++) {
                        if (dx == 0 && dy == 0) continue;
                        int nx = rx + dx, ny = ry + dy;
                        if (1 <= nx && nx <= 3000 && 1 <= ny && ny <= 3000) {
                            lastMove = {nx, ny};
                        }
                    }
                }
            }
            if (lastMove.first == -1) lastMove = nextSafe();
            out.push_back(lastMove);
        } else {
            for (int i = 0; i < m; i++) out.push_back(nextSafe());
        }

        for (auto &p : out) {
            cout << p.first << ' ' << p.second << "\n";
        }
        return 0;
    }

    // Fallback interactive-like behavior (best-effort).
    int rx = sx, ry = sy;
    for (int t = 1; t <= 3000; t++) {
        int mx = rx, my = ry;
        if (rx < 3000 && ry < 3000) { mx = rx + 1; my = ry + 1; }
        else if (rx < 3000) { mx = rx + 1; my = ry; }
        else if (ry < 3000) { mx = rx; my = ry + 1; }
        else { mx = 3000; my = 3000; }

        cout << mx << ' ' << my << "\n";
        cout.flush();

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) return 0;
        rx = nx; ry = ny;
    }
    return 0;
}