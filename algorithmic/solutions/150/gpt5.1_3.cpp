#include <bits/stdc++.h>
using namespace std;

struct Placement {
    int sid;
    unsigned char row, col, len;
};

struct CellPl {
    int pid;
    unsigned char t;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<string> S(M);
    for (int i = 0; i < M; i++) cin >> S[i];

    const int RSEL = 4;            // number of rows per string to allow placements
    const double TIME_LIMIT = 0.9; // seconds for simulated annealing

    int N2 = N * N;

    // Random generator
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    // Initialize grid randomly
    vector<string> grid(N, string(N, 'A'));
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            grid[r][c] = 'A' + (int)(rng() % 8);
        }
    }

    // Build placements (horizontal only, limited rows per string)
    vector<Placement> placements;
    placements.reserve(M * RSEL * N);

    vector<vector<CellPl>> cellPlacements(N2);
    vector<int> rowIdx(N);
    iota(rowIdx.begin(), rowIdx.end(), 0);

    for (int i = 0; i < M; i++) {
        int L = (int)S[i].size();
        shuffle(rowIdx.begin(), rowIdx.end(), rng);
        int useRows = min(RSEL, N);
        for (int ri = 0; ri < useRows; ri++) {
            int r = rowIdx[ri];
            for (int c = 0; c < N; c++) {
                int pid = (int)placements.size();
                placements.push_back(Placement{ i, (unsigned char)r, (unsigned char)c, (unsigned char)L });
                for (int t = 0; t < L; t++) {
                    int cc = (c + t) % N;
                    int cellId = r * N + cc;
                    cellPlacements[cellId].push_back(CellPl{ pid, (unsigned char)t });
                }
            }
        }
    }

    int P = (int)placements.size();

    // Evaluation structures
    vector<int> matchesCount(P, 0);
    vector<int> validPlacementCount(M, 0);
    vector<char> isMatched(M, 0);
    int totalMatched = 0;

    // Initial evaluation
    for (int pid = 0; pid < P; pid++) {
        const auto &pl = placements[pid];
        int sid = pl.sid;
        int L = pl.len;
        int r = pl.row;
        int c0 = pl.col;
        int mc = 0;
        const string &str = S[sid];
        for (int t = 0; t < L; t++) {
            int cc = (c0 + t) % N;
            if (grid[r][cc] == str[t]) mc++;
        }
        matchesCount[pid] = mc;
        if (mc == L) {
            validPlacementCount[sid]++;
            if (!isMatched[sid]) {
                isMatched[sid] = 1;
                totalMatched++;
            }
        }
    }

    int bestScore = totalMatched;
    vector<string> bestGrid = grid;

    // Simulated annealing / hill-climbing
    auto timeStart = chrono::steady_clock::now();

    vector<int> deltaFull(M, 0);
    vector<char> sidUsed(M, 0);
    vector<int> affectedSids;
    affectedSids.reserve(2048);

    auto getTime = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - timeStart).count();
    };

    double startTemp = 3.0;
    double endTemp = 0.1;

    while (true) {
        double tElapsed = getTime();
        if (tElapsed > TIME_LIMIT) break;
        double progress = tElapsed / TIME_LIMIT;
        double temp = startTemp + (endTemp - startTemp) * progress;

        int r = (int)(rng() % N);
        int c = (int)(rng() % N);
        int cellId = r * N + c;
        char oldCh = grid[r][c];
        char newCh;
        do {
            newCh = 'A' + (int)(rng() % 8);
        } while (newCh == oldCh);

        auto &vec = cellPlacements[cellId];

        int deltaC = 0;
        affectedSids.clear();

        for (const auto &cp : vec) {
            int pid = cp.pid;
            const auto &pl = placements[pid];
            int sid = pl.sid;
            int L = pl.len;
            int before = matchesCount[pid];
            char sch = S[sid][cp.t];
            bool oldMatch = (oldCh == sch);
            bool newMatch = (newCh == sch);
            if (oldMatch == newMatch) continue;
            int after = before + (newMatch - oldMatch);
            bool wasFull = (before == L);
            bool nowFull = (after == L);
            if (wasFull == nowFull) continue;

            if (!sidUsed[sid]) {
                sidUsed[sid] = 1;
                affectedSids.push_back(sid);
            }
            if (!wasFull && nowFull) deltaFull[sid]++;
            else if (wasFull && !nowFull) deltaFull[sid]--;
        }

        for (int sid : affectedSids) {
            int oldValid = validPlacementCount[sid];
            int newValid = oldValid + deltaFull[sid];
            bool wasMatch = (oldValid > 0);
            bool nowMatch = (newValid > 0);
            if (!wasMatch && nowMatch) deltaC++;
            else if (wasMatch && !nowMatch) deltaC--;
        }

        bool accept;
        if (deltaC >= 0) {
            accept = true;
        } else {
            double prob = exp((double)deltaC / temp);
            uint64_t rnd = rng();
            double rand01 = (rnd >> 11) * (1.0 / 9007199254740992.0); // 53-bit / 2^53
            accept = (rand01 < prob);
        }

        if (accept) {
            grid[r][c] = newCh;
            for (const auto &cp : vec) {
                int pid = cp.pid;
                auto &pl = placements[pid];
                int sid = pl.sid;
                int L = pl.len;
                int before = matchesCount[pid];
                char sch = S[sid][cp.t];
                bool oldMatch = (oldCh == sch);
                bool newMatch = (newCh == sch);
                if (oldMatch == newMatch) continue;
                int after = before + (newMatch - oldMatch);
                bool wasFull = (before == L);
                bool nowFull = (after == L);
                matchesCount[pid] = after;

                if (!wasFull && nowFull) {
                    int v = ++validPlacementCount[sid];
                    if (v == 1) totalMatched++;
                } else if (wasFull && !nowFull) {
                    int v = --validPlacementCount[sid];
                    if (v == 0) totalMatched--;
                }
            }
            if (totalMatched > bestScore) {
                bestScore = totalMatched;
                bestGrid = grid;
            }
        }

        for (int sid : affectedSids) {
            deltaFull[sid] = 0;
            sidUsed[sid] = 0;
        }
    }

    // Output best found grid
    for (int r = 0; r < N; r++) {
        cout << bestGrid[r] << '\n';
    }

    return 0;
}