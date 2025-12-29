#include <bits/stdc++.h>
using namespace std;

struct Action {
    char dir;
    int p;      // row index for L/R, column index for U/D
    int dist;   // number of shifts in dir, and also in opposite dir
    int removed;
    int cost() const { return 2 * dist; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<string> g(N);
    for (int i = 0; i < N; i++) cin >> g[i];

    vector<vector<int>> rowPrefF(N, vector<int>(N + 1, 0));
    vector<vector<int>> colPrefF(N, vector<int>(N + 1, 0));
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) rowPrefF[i][j + 1] = rowPrefF[i][j] + (g[i][j] == 'o');
    }
    for (int j = 0; j < N; j++) {
        for (int i = 0; i < N; i++) colPrefF[j][i + 1] = colPrefF[j][i] + (g[i][j] == 'o');
    }

    vector<vector<unsigned char>> upClear(N, vector<unsigned char>(N, 0));
    vector<vector<unsigned char>> downClear(N, vector<unsigned char>(N, 0));
    vector<vector<unsigned char>> leftClear(N, vector<unsigned char>(N, 0));
    vector<vector<unsigned char>> rightClear(N, vector<unsigned char>(N, 0));

    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) {
        upClear[i][j] = (colPrefF[j][i] == 0);
        downClear[i][j] = ((colPrefF[j][N] - colPrefF[j][i + 1]) == 0);
        leftClear[i][j] = (rowPrefF[i][j] == 0);
        rightClear[i][j] = ((rowPrefF[i][N] - rowPrefF[i][j + 1]) == 0);
    }

    auto opp = [&](char d) -> char {
        if (d == 'U') return 'D';
        if (d == 'D') return 'U';
        if (d == 'L') return 'R';
        return 'L';
    };

    auto evalCandidate = [&](char d, int i, int j) -> optional<Action> {
        Action a;
        a.dir = d;
        if (d == 'U') {
            if (!upClear[i][j]) return nullopt;
            a.p = j;
            a.dist = i + 1;
            int cnt = 0;
            for (int r = 0; r < a.dist; r++) {
                if (g[r][j] == 'o') return nullopt;
                if (g[r][j] == 'x') cnt++;
            }
            a.removed = cnt;
            return a;
        } else if (d == 'D') {
            if (!downClear[i][j]) return nullopt;
            a.p = j;
            a.dist = N - i;
            int cnt = 0;
            for (int r = N - a.dist; r < N; r++) {
                if (g[r][j] == 'o') return nullopt;
                if (g[r][j] == 'x') cnt++;
            }
            a.removed = cnt;
            return a;
        } else if (d == 'L') {
            if (!leftClear[i][j]) return nullopt;
            a.p = i;
            a.dist = j + 1;
            int cnt = 0;
            for (int c = 0; c < a.dist; c++) {
                if (g[i][c] == 'o') return nullopt;
                if (g[i][c] == 'x') cnt++;
            }
            a.removed = cnt;
            return a;
        } else { // 'R'
            if (!rightClear[i][j]) return nullopt;
            a.p = i;
            a.dist = N - j;
            int cnt = 0;
            for (int c = N - a.dist; c < N; c++) {
                if (g[i][c] == 'o') return nullopt;
                if (g[i][c] == 'x') cnt++;
            }
            a.removed = cnt;
            return a;
        }
    };

    auto better = [&](const Action& A, const Action& B) -> bool {
        // minimize cost/removed
        long long lhs = 1LL * A.cost() * B.removed;
        long long rhs = 1LL * B.cost() * A.removed;
        if (lhs != rhs) return lhs < rhs;
        if (A.removed != B.removed) return A.removed > B.removed;
        if (A.cost() != B.cost()) return A.cost() < B.cost();
        if (A.dir != B.dir) return A.dir < B.dir;
        return A.p < B.p;
    };

    vector<pair<char,int>> ops;
    const int LIMIT = 4 * N * N;

    while (true) {
        vector<pair<int,int>> onis;
        onis.reserve(40);
        for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) if (g[i][j] == 'x') onis.emplace_back(i, j);
        if (onis.empty()) break;

        bool found = false;
        Action best{};

        for (auto [i, j] : onis) {
            for (char d : {'U','D','L','R'}) {
                auto cand = evalCandidate(d, i, j);
                if (!cand) continue;
                if (cand->removed <= 0) continue; // should not happen
                if (!found || better(*cand, best)) {
                    best = *cand;
                    found = true;
                }
            }
        }

        if (!found) break; // should not happen

        if ((int)ops.size() + best.cost() > LIMIT) break; // fallback: output partial (still legal)

        for (int t = 0; t < best.dist; t++) ops.push_back({best.dir, best.p});
        char od = opp(best.dir);
        for (int t = 0; t < best.dist; t++) ops.push_back({od, best.p});

        // Apply net effect: wipe the corresponding segment.
        if (best.dir == 'U') {
            int col = best.p;
            for (int r = 0; r < best.dist; r++) if (g[r][col] != 'o') g[r][col] = '.';
        } else if (best.dir == 'D') {
            int col = best.p;
            for (int r = N - best.dist; r < N; r++) if (g[r][col] != 'o') g[r][col] = '.';
        } else if (best.dir == 'L') {
            int row = best.p;
            for (int c = 0; c < best.dist; c++) if (g[row][c] != 'o') g[row][c] = '.';
        } else { // 'R'
            int row = best.p;
            for (int c = N - best.dist; c < N; c++) if (g[row][c] != 'o') g[row][c] = '.';
        }
    }

    for (auto &[d, p] : ops) {
        cout << d << ' ' << p << "\n";
    }
    return 0;
}