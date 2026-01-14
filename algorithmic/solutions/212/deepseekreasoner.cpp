#include <bits/stdc++.h>
using namespace std;

int n, m, L, R, Sx, Sy, Lq, s;
vector<int> q;

// check if q is a subsequence of seq
bool is_subseq(const vector<int>& seq) {
    int idx = 0;
    for (int x : seq) {
        if (idx < Lq && x == q[idx]) idx++;
    }
    return idx == Lq;
}

// compute extra moves for the jump between parts, and feasibility
// returns -1 if infeasible, otherwise extra moves beyond 1 for that transition
int compute_extra(int a, int b, int col, int L, int R, int m) {
    if (abs(a - b) == 1) return 0;
    if (col == L && L > 1) return abs(a - b) + 1;
    if (col == R && R < m) return abs(a - b) + 1;
    return -1; // infeasible
}

// generate the full path for a given sequence seq
vector<pair<int,int>> generate_path(const vector<int>& seq) {
    vector<pair<int,int>> path;
    bool first_row = true;
    for (size_t i = 0; i < seq.size(); i++) {
        int row = seq[i];
        int start_col = (i % 2 == 0) ? L : R; // parity: 0-indexed, even -> odd position -> L
        // generate cells for this row
        vector<pair<int,int>> row_cells;
        if (start_col == L) {
            for (int y = L; y <= R; y++) row_cells.emplace_back(row, y);
        } else {
            for (int y = R; y >= L; y--) row_cells.emplace_back(row, y);
        }
        if (first_row) {
            path.insert(path.end(), row_cells.begin(), row_cells.end());
            first_row = false;
        } else {
            // skip the first cell, already visited as last cell of previous transition
            path.insert(path.end(), row_cells.begin() + 1, row_cells.end());
        }
        // generate transition to next row if exists
        if (i + 1 < seq.size()) {
            int next_row = seq[i+1];
            int next_start_col = ((i+1) % 2 == 0) ? L : R;
            // current end column after finishing this row
            int cur_end_col = (start_col == L) ? R : L;
            int col = cur_end_col; // should equal next_start_col
            if (abs(row - next_row) == 1) {
                // direct vertical step
                path.emplace_back(next_row, col);
            } else {
                // use corridor
                if (col == L) {
                    // left corridor
                    path.emplace_back(row, L-1);
                    int step = (next_row > row) ? 1 : -1;
                    for (int r = row + step; r != next_row; r += step) {
                        path.emplace_back(r, L-1);
                    }
                    path.emplace_back(next_row, L-1);
                    path.emplace_back(next_row, L);
                } else { // col == R
                    path.emplace_back(row, R+1);
                    int step = (next_row > row) ? 1 : -1;
                    for (int r = row + step; r != next_row; r += step) {
                        path.emplace_back(r, R+1);
                    }
                    path.emplace_back(next_row, R+1);
                    path.emplace_back(next_row, R);
                }
            }
        }
    }
    return path;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    q.resize(Lq);
    for (int i = 0; i < Lq; i++) cin >> q[i];

    // Sy must equal L as guaranteed
    // generate two candidate sequences
    vector<int> seqA, seqB;

    // seqA: Sx -> n, then Sx-1 -> 1
    for (int i = Sx; i <= n; i++) seqA.push_back(i);
    for (int i = Sx - 1; i >= 1; i--) seqA.push_back(i);

    // seqB: Sx -> 1, then Sx+1 -> n
    for (int i = Sx; i >= 1; i--) seqB.push_back(i);
    for (int i = Sx + 1; i <= n; i++) seqB.push_back(i);

    // check feasibility and compute extra moves for each
    int extraA = -1, extraB = -1;
    bool feasibleA = false, feasibleB = false;

    // check seqA
    if (is_subseq(seqA)) {
        int k = n - Sx + 1; // length of first part
        int colA = (k % 2 == 1) ? R : L;
        int aA = n;
        int bA = Sx - 1;
        if (bA < 1) {
            // second part empty
            extraA = 0;
            feasibleA = true;
        } else {
            extraA = compute_extra(aA, bA, colA, L, R, m);
            if (extraA != -1) feasibleA = true;
        }
    }

    // check seqB
    if (is_subseq(seqB)) {
        int k = Sx; // length of first part
        int colB = (k % 2 == 1) ? R : L;
        int aB = 1;
        int bB = Sx + 1;
        if (bB > n) {
            extraB = 0;
            feasibleB = true;
        } else {
            extraB = compute_extra(aB, bB, colB, L, R, m);
            if (extraB != -1) feasibleB = true;
        }
    }

    if (!feasibleA && !feasibleB) {
        cout << "NO\n";
        return 0;
    }

    // choose the one with smaller total moves
    int total_moves_base = n * (R - L) + (n - 1);
    int totalA = total_moves_base + (feasibleA ? extraA : INT_MAX);
    int totalB = total_moves_base + (feasibleB ? extraB : INT_MAX);

    vector<int> chosen_seq;
    if (totalA <= totalB && feasibleA) {
        chosen_seq = seqA;
    } else if (feasibleB) {
        chosen_seq = seqB;
    } else {
        cout << "NO\n";
        return 0;
    }

    vector<pair<int,int>> path = generate_path(chosen_seq);
    cout << "YES\n";
    cout << path.size() << "\n";
    for (auto [x, y] : path) {
        cout << x << " " << y << "\n";
    }
    return 0;
}