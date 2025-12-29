#include <bits/stdc++.h>
using namespace std;

struct Candidate {
    char dir;          // 'U','D','L','R'
    int p;             // row or column index
    int k;             // number of shifts each way
    int cost;          // 2*k
    vector<int> cover; // indices of Oni covered
};

struct EvalResult {
    long long score;
};

void addOpsFromCandidate(const Candidate &c, vector<pair<char,int>> &ops) {
    char d = c.dir;
    int p = c.p;
    int k = c.k;
    if (d == 'U') {
        for (int t = 0; t < k; ++t) ops.emplace_back('U', p);
        for (int t = 0; t < k; ++t) ops.emplace_back('D', p);
    } else if (d == 'D') {
        for (int t = 0; t < k; ++t) ops.emplace_back('D', p);
        for (int t = 0; t < k; ++t) ops.emplace_back('U', p);
    } else if (d == 'L') {
        for (int t = 0; t < k; ++t) ops.emplace_back('L', p);
        for (int t = 0; t < k; ++t) ops.emplace_back('R', p);
    } else if (d == 'R') {
        for (int t = 0; t < k; ++t) ops.emplace_back('R', p);
        for (int t = 0; t < k; ++t) ops.emplace_back('L', p);
    }
}

EvalResult evaluateSolution(const vector<string> &initialBoard,
                            const vector<pair<char,int>> &ops,
                            int N) {
    const long long NEG_INF = (long long)-4e18;
    int limit = 4 * N * N;
    if ((int)ops.size() > limit) {
        return {NEG_INF};
    }
    vector<string> board = initialBoard;
    int Finit = 0;
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            if (board[i][j] == 'o') ++Finit;

    for (auto &op : ops) {
        char d = op.first;
        int p = op.second;
        if (d == 'U') {
            for (int r = 0; r < N - 1; ++r) board[r][p] = board[r + 1][p];
            board[N - 1][p] = '.';
        } else if (d == 'D') {
            for (int r = N - 1; r >= 1; --r) board[r][p] = board[r - 1][p];
            board[0][p] = '.';
        } else if (d == 'L') {
            for (int c = 0; c < N - 1; ++c) board[p][c] = board[p][c + 1];
            board[p][N - 1] = '.';
        } else if (d == 'R') {
            for (int c = N - 1; c >= 1; --c) board[p][c] = board[p][c - 1];
            board[p][0] = '.';
        }
    }

    int X = 0, Fleft = 0;
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'x') ++X;
            else if (board[i][j] == 'o') ++Fleft;
        }
    int Y = Finit - Fleft;
    long long T = (long long)ops.size();
    long long score;
    if (X == 0 && Y == 0) {
        score = 8LL * N * N - T;
    } else {
        score = 4LL * N * N - 1LL * N * (X + Y);
    }
    return {score};
}

vector<pair<char,int>> buildSimpleOps(
    int N,
    const vector<string> &C,
    const vector<pair<int,int>> &oniPos
) {
    vector<pair<char,int>> ops;
    for (auto [i, j] : oniPos) {
        bool upOk = true, downOk = true, leftOk = true, rightOk = true;

        for (int r = 0; r < i; ++r)
            if (C[r][j] == 'o') { upOk = false; break; }

        for (int r = i + 1; r < N; ++r)
            if (C[r][j] == 'o') { downOk = false; break; }

        for (int c = 0; c < j; ++c)
            if (C[i][c] == 'o') { leftOk = false; break; }

        for (int c = j + 1; c < N; ++c)
            if (C[i][c] == 'o') { rightOk = false; break; }

        int bestCost = INT_MAX;
        char bestDir = 'U';
        int bestK = 0;

        if (upOk) {
            int k = i + 1;
            int cost = 2 * k;
            if (cost < bestCost) {
                bestCost = cost;
                bestDir = 'U';
                bestK = k;
            }
        }
        if (downOk) {
            int k = N - i;
            int cost = 2 * k;
            if (cost < bestCost) {
                bestCost = cost;
                bestDir = 'D';
                bestK = k;
            }
        }
        if (leftOk) {
            int k = j + 1;
            int cost = 2 * k;
            if (cost < bestCost) {
                bestCost = cost;
                bestDir = 'L';
                bestK = k;
            }
        }
        if (rightOk) {
            int k = N - j;
            int cost = 2 * k;
            if (cost < bestCost) {
                bestCost = cost;
                bestDir = 'R';
                bestK = k;
            }
        }

        if (bestDir == 'U') {
            for (int t = 0; t < bestK; ++t) ops.emplace_back('U', j);
            for (int t = 0; t < bestK; ++t) ops.emplace_back('D', j);
        } else if (bestDir == 'D') {
            for (int t = 0; t < bestK; ++t) ops.emplace_back('D', j);
            for (int t = 0; t < bestK; ++t) ops.emplace_back('U', j);
        } else if (bestDir == 'L') {
            for (int t = 0; t < bestK; ++t) ops.emplace_back('L', i);
            for (int t = 0; t < bestK; ++t) ops.emplace_back('R', i);
        } else if (bestDir == 'R') {
            for (int t = 0; t < bestK; ++t) ops.emplace_back('R', i);
            for (int t = 0; t < bestK; ++t) ops.emplace_back('L', i);
        }
    }
    return ops;
}

vector<Candidate> buildCandidates(
    int N,
    const vector<string> &C,
    const vector<pair<int,int>> &oniPos,
    const vector<vector<int>> &oniIdx
) {
    vector<Candidate> cands;
    int K = (int)oniPos.size();
    (void)K;

    for (int id = 0; id < (int)oniPos.size(); ++id) {
        int i = oniPos[id].first;
        int j = oniPos[id].second;

        // Up
        bool upOk = true;
        for (int r = 0; r < i; ++r)
            if (C[r][j] == 'o') { upOk = false; break; }
        if (upOk) {
            Candidate can;
            can.dir = 'U';
            can.p = j;
            can.k = i + 1;
            can.cost = 2 * can.k;
            for (int r = 0; r <= i; ++r) {
                int idx = oniIdx[r][j];
                if (idx != -1) can.cover.push_back(idx);
            }
            cands.push_back(move(can));
        }

        // Down
        bool downOk = true;
        for (int r = i + 1; r < N; ++r)
            if (C[r][j] == 'o') { downOk = false; break; }
        if (downOk) {
            Candidate can;
            can.dir = 'D';
            can.p = j;
            can.k = N - i;
            can.cost = 2 * can.k;
            for (int r = i; r < N; ++r) {
                int idx = oniIdx[r][j];
                if (idx != -1) can.cover.push_back(idx);
            }
            cands.push_back(move(can));
        }

        // Left
        bool leftOk = true;
        for (int c = 0; c < j; ++c)
            if (C[i][c] == 'o') { leftOk = false; break; }
        if (leftOk) {
            Candidate can;
            can.dir = 'L';
            can.p = i;
            can.k = j + 1;
            can.cost = 2 * can.k;
            for (int c = 0; c <= j; ++c) {
                int idx = oniIdx[i][c];
                if (idx != -1) can.cover.push_back(idx);
            }
            cands.push_back(move(can));
        }

        // Right
        bool rightOk = true;
        for (int c = j + 1; c < N; ++c)
            if (C[i][c] == 'o') { rightOk = false; break; }
        if (rightOk) {
            Candidate can;
            can.dir = 'R';
            can.p = i;
            can.k = N - j;
            can.cost = 2 * can.k;
            for (int c = j; c < N; ++c) {
                int idx = oniIdx[i][c];
                if (idx != -1) can.cover.push_back(idx);
            }
            cands.push_back(move(can));
        }
    }
    return cands;
}

vector<pair<char,int>> buildGreedyOps(
    int N,
    const vector<string> &C,
    const vector<pair<int,int>> &oniPos,
    const vector<vector<int>> &oniIdx
) {
    vector<Candidate> cands = buildCandidates(N, C, oniPos, oniIdx);
    int K = (int)oniPos.size();
    int M = (int)cands.size();

    vector<bool> covered(K, false);
    vector<bool> used(M, false);
    vector<pair<char,int>> ops;

    auto anyUncovered = [&]() -> bool {
        for (int i = 0; i < K; ++i)
            if (!covered[i]) return true;
        return false;
    };

    while (anyUncovered()) {
        int bestIdx = -1;
        double bestScore = -1.0;
        int bestCost = 0;

        for (int ci = 0; ci < M; ++ci) {
            if (used[ci]) continue;
            int gain = 0;
            for (int oi : cands[ci].cover)
                if (!covered[oi]) ++gain;
            if (gain == 0) continue;
            int cost = cands[ci].cost;
            double score = (double)gain / (double)cost;
            if (score > bestScore + 1e-9 ||
                (fabs(score - bestScore) <= 1e-9 && cost < bestCost)) {
                bestScore = score;
                bestIdx = ci;
                bestCost = cost;
            }
        }

        if (bestIdx == -1) break;

        used[bestIdx] = true;
        addOpsFromCandidate(cands[bestIdx], ops);
        for (int oi : cands[bestIdx].cover) covered[oi] = true;
    }

    return ops;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    vector<pair<int,int>> oniPos;
    vector<vector<int>> oniIdx(N, vector<int>(N, -1));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] == 'x') {
                int id = (int)oniPos.size();
                oniPos.emplace_back(i, j);
                oniIdx[i][j] = id;
            }
        }
    }

    vector<pair<char,int>> opsSimple = buildSimpleOps(N, C, oniPos);
    vector<pair<char,int>> opsGreedy = buildGreedyOps(N, C, oniPos, oniIdx);

    EvalResult resSimple = evaluateSolution(C, opsSimple, N);
    EvalResult resGreedy = evaluateSolution(C, opsGreedy, N);

    vector<pair<char,int>> &bestOps =
        (resGreedy.score > resSimple.score ? opsGreedy : opsSimple);

    for (auto &op : bestOps) {
        cout << op.first << ' ' << op.second << '\n';
    }

    return 0;
}