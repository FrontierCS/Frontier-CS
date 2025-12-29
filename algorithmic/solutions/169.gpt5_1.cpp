#include <bits/stdc++.h>
using namespace std;

struct MoveOp {
    char d;
    int p;
};

struct Candidate {
    char dir; // 'U','D','L','R'
    int p;    // column for U/D, row for L/R
    int steps; // number of first-direction shifts
    int cost;  // 2*steps
    int benefit; // number of x removed
    int removedMinSum; // sum of min costs of removed x's
    double ratio; // benefit / cost
    bool valid;
    Candidate():dir('U'),p(0),steps(0),cost(0),benefit(0),removedMinSum(0),ratio(-1.0),valid(false){}
};

int N;
vector<string> board;
vector<MoveOp> ops;
int T_used = 0;
int maxOps;

int Xcount = 0;
int Yremoved = 0;

void shiftColUp(int j) {
    // remove top
    if (board[0][j] == 'x') Xcount--;
    else if (board[0][j] == 'o') Yremoved++;
    for (int i = 0; i < N-1; i++) board[i][j] = board[i+1][j];
    board[N-1][j] = '.';
    ops.push_back({'U', j});
    T_used++;
}

void shiftColDown(int j) {
    if (board[N-1][j] == 'x') Xcount--;
    else if (board[N-1][j] == 'o') Yremoved++;
    for (int i = N-1; i >= 1; i--) board[i][j] = board[i-1][j];
    board[0][j] = '.';
    ops.push_back({'D', j});
    T_used++;
}

void shiftRowLeft(int i) {
    if (board[i][0] == 'x') Xcount--;
    else if (board[i][0] == 'o') Yremoved++;
    for (int j = 0; j < N-1; j++) board[i][j] = board[i][j+1];
    board[i][N-1] = '.';
    ops.push_back({'L', i});
    T_used++;
}

void shiftRowRight(int i) {
    if (board[i][N-1] == 'x') Xcount--;
    else if (board[i][N-1] == 'o') Yremoved++;
    for (int j = N-1; j >= 1; j--) board[i][j] = board[i][j-1];
    board[i][0] = '.';
    ops.push_back({'R', i});
    T_used++;
}

int minCostForX(int i, int j) {
    const int INF = 1e9;
    int dU = INF, dD = INF, dL = INF, dR = INF;
    bool safe = true;
    for (int r = 0; r < i; r++) if (board[r][j] == 'o') { safe = false; break; }
    if (safe) dU = i + 1;
    safe = true;
    for (int r = i+1; r < N; r++) if (board[r][j] == 'o') { safe = false; break; }
    if (safe) dD = N - i;
    safe = true;
    for (int c = 0; c < j; c++) if (board[i][c] == 'o') { safe = false; break; }
    if (safe) dL = j + 1;
    safe = true;
    for (int c = j+1; c < N; c++) if (board[i][c] == 'o') { safe = false; break; }
    if (safe) dR = N - j;
    int d = min(min(dU, dD), min(dL, dR));
    if (d >= INF) d = 2 * N; // should not happen due to guarantee
    return 2 * d;
}

void applyCandidate(const Candidate& c) {
    int steps = c.steps;
    if (c.dir == 'U') {
        for (int k = 0; k < steps; k++) shiftColUp(c.p);
        for (int k = 0; k < steps; k++) shiftColDown(c.p);
    } else if (c.dir == 'D') {
        for (int k = 0; k < steps; k++) shiftColDown(c.p);
        for (int k = 0; k < steps; k++) shiftColUp(c.p);
    } else if (c.dir == 'L') {
        for (int k = 0; k < steps; k++) shiftRowLeft(c.p);
        for (int k = 0; k < steps; k++) shiftRowRight(c.p);
    } else if (c.dir == 'R') {
        for (int k = 0; k < steps; k++) shiftRowRight(c.p);
        for (int k = 0; k < steps; k++) shiftRowLeft(c.p);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> N;
    board.resize(N);
    for (int i = 0; i < N; i++) cin >> board[i];
    maxOps = 4 * N * N;

    Xcount = 0;
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            if (board[i][j] == 'x') Xcount++;

    while (Xcount > 0 && T_used < maxOps) {
        // compute minCost for all current x's and their sum
        vector<vector<int>> minCost(N, vector<int>(N, 0));
        int sumMinCost = 0;
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                if (board[i][j] == 'x') {
                    int c = minCostForX(i, j);
                    minCost[i][j] = c;
                    sumMinCost += c;
                }
            }
        }

        // If already ensured we can finish with remaining budget by individual removals
        // choose best ratio candidate under budget constraints
        Candidate best;
        best.valid = false;
        best.ratio = -1.0;

        auto consider = [&](const Candidate& cand){
            if (!cand.valid) return;
            // budget check: T + cand.cost + (sumMinCost - cand.removedMinSum) <= maxOps
            long long futureBound = (long long)T_used + cand.cost + (sumMinCost - cand.removedMinSum);
            if (futureBound > maxOps) return;
            double r = cand.ratio;
            if (!best.valid || r > best.ratio + 1e-15 ||
                (fabs(r - best.ratio) <= 1e-15 && (cand.benefit > best.benefit ||
                 (cand.benefit == best.benefit && cand.cost < best.cost)))) {
                best = cand;
            }
        };

        // Generate candidates
        // Columns: Up and Down
        for (int j = 0; j < N; j++) {
            // Up
            int cnt = 0;
            int sumMin = 0;
            bool blocked = false;
            for (int i = 0; i < N; i++) {
                if (board[i][j] == 'o') { blocked = true; break; }
                if (board[i][j] == 'x') {
                    cnt++;
                    sumMin += minCost[i][j];
                    Candidate cand;
                    cand.valid = true;
                    cand.dir = 'U';
                    cand.p = j;
                    cand.steps = i + 1;
                    cand.cost = 2 * cand.steps;
                    cand.benefit = cnt;
                    cand.removedMinSum = sumMin;
                    cand.ratio = (double)cand.benefit / max(1, cand.cost);
                    consider(cand);
                }
            }
            // Down
            cnt = 0;
            sumMin = 0;
            for (int i = N-1; i >= 0; i--) {
                if (board[i][j] == 'o') break;
                if (board[i][j] == 'x') {
                    cnt++;
                    sumMin += minCost[i][j];
                    Candidate cand;
                    cand.valid = true;
                    cand.dir = 'D';
                    cand.p = j;
                    cand.steps = N - i;
                    cand.cost = 2 * cand.steps;
                    cand.benefit = cnt;
                    cand.removedMinSum = sumMin;
                    cand.ratio = (double)cand.benefit / max(1, cand.cost);
                    consider(cand);
                }
            }
        }

        // Rows: Left and Right
        for (int i = 0; i < N; i++) {
            // Left
            int cnt = 0;
            int sumMin = 0;
            for (int j = 0; j < N; j++) {
                if (board[i][j] == 'o') break;
                if (board[i][j] == 'x') {
                    cnt++;
                    sumMin += minCost[i][j];
                    Candidate cand;
                    cand.valid = true;
                    cand.dir = 'L';
                    cand.p = i;
                    cand.steps = j + 1;
                    cand.cost = 2 * cand.steps;
                    cand.benefit = cnt;
                    cand.removedMinSum = sumMin;
                    cand.ratio = (double)cand.benefit / max(1, cand.cost);
                    consider(cand);
                }
            }
            // Right
            cnt = 0;
            sumMin = 0;
            for (int j = N-1; j >= 0; j--) {
                if (board[i][j] == 'o') break;
                if (board[i][j] == 'x') {
                    cnt++;
                    sumMin += minCost[i][j];
                    Candidate cand;
                    cand.valid = true;
                    cand.dir = 'R';
                    cand.p = i;
                    cand.steps = N - j;
                    cand.cost = 2 * cand.steps;
                    cand.benefit = cnt;
                    cand.removedMinSum = sumMin;
                    cand.ratio = (double)cand.benefit / max(1, cand.cost);
                    consider(cand);
                }
            }
        }

        if (!best.valid) {
            // As a fallback (shouldn't happen due to budget invariant), pick any minimal individual x removal that fits remaining ops
            int bestCost = INT_MAX;
            int bi = -1, bj = -1;
            for (int i = 0; i < N; i++) {
                for (int j = 0; j < N; j++) if (board[i][j] == 'x') {
                    int c = minCost[i][j];
                    if (T_used + c <= maxOps && c < bestCost) {
                        bestCost = c; bi = i; bj = j;
                    }
                }
            }
            if (bi == -1) break; // cannot proceed
            // Find direction achieving minCost for (bi,bj)
            int target_i = bi, target_j = bj;
            // Try four directions to match c
            // U
            bool safe = true;
            for (int r = 0; r < bi; r++) if (board[r][bj] == 'o') { safe = false; break; }
            if (safe && 2*(bi+1) == bestCost) {
                Candidate cand;
                cand.valid = true; cand.dir = 'U'; cand.p = bj; cand.steps = bi+1; cand.cost = bestCost;
                applyCandidate(cand);
                continue;
            }
            // D
            safe = true;
            for (int r = bi+1; r < N; r++) if (board[r][bj] == 'o') { safe = false; break; }
            if (safe && 2*(N - bi) == bestCost) {
                Candidate cand;
                cand.valid = true; cand.dir = 'D'; cand.p = bj; cand.steps = N - bi; cand.cost = bestCost;
                applyCandidate(cand);
                continue;
            }
            // L
            safe = true;
            for (int c = 0; c < bj; c++) if (board[bi][c] == 'o') { safe = false; break; }
            if (safe && 2*(bj+1) == bestCost) {
                Candidate cand;
                cand.valid = true; cand.dir = 'L'; cand.p = bi; cand.steps = bj+1; cand.cost = bestCost;
                applyCandidate(cand);
                continue;
            }
            // R
            safe = true;
            for (int c = bj+1; c < N; c++) if (board[bi][c] == 'o') { safe = false; break; }
            if (safe && 2*(N - bj) == bestCost) {
                Candidate cand;
                cand.valid = true; cand.dir = 'R'; cand.p = bi; cand.steps = N - bj; cand.cost = bestCost;
                applyCandidate(cand);
                continue;
            }
            // As a last resort, pick any candidate that fits remaining ops straightforwardly
            // Find any x and any safe direction
            bool done = false;
            for (int i = 0; i < N && !done; i++) for (int j = 0; j < N && !done; j++) if (board[i][j] == 'x') {
                // try directions
                // U
                bool ok = true;
                for (int r = 0; r < i; r++) if (board[r][j] == 'o') { ok = false; break; }
                if (ok && T_used + 2*(i+1) <= maxOps) { Candidate cand; cand.valid=true;cand.dir='U';cand.p=j;cand.steps=i+1;applyCandidate(cand); done = true; break; }
                // D
                ok = true;
                for (int r = i+1; r < N; r++) if (board[r][j] == 'o') { ok = false; break; }
                if (ok && T_used + 2*(N-i) <= maxOps) { Candidate cand; cand.valid=true;cand.dir='D';cand.p=j;cand.steps=N-i;applyCandidate(cand); done = true; break; }
                // L
                ok = true;
                for (int c = 0; c < j; c++) if (board[i][c] == 'o') { ok = false; break; }
                if (ok && T_used + 2*(j+1) <= maxOps) { Candidate cand; cand.valid=true;cand.dir='L';cand.p=i;cand.steps=j+1;applyCandidate(cand); done = true; break; }
                // R
                ok = true;
                for (int c = j+1; c < N; c++) if (board[i][c] == 'o') { ok = false; break; }
                if (ok && T_used + 2*(N-j) <= maxOps) { Candidate cand; cand.valid=true;cand.dir='R';cand.p=i;cand.steps=N-j;applyCandidate(cand); done = true; break; }
            }
            if (!done) break;
        } else {
            applyCandidate(best);
        }

        if (T_used >= maxOps) break;
        if (Yremoved > 0) {
            // Should not happen with our checks, but if it does, stop to avoid further penalties
            break;
        }
    }

    // Output operations
    for (auto &m : ops) {
        cout << m.d << " " << m.p << "\n";
    }
    return 0;
}