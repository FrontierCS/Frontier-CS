#include <bits/stdc++.h>
using namespace std;

int main() {
    int si, sj;
    cin >> si >> sj;
    vector<vector<int>> T(50, vector<int>(50));
    int max_tid = 0;
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            cin >> T[i][j];
            max_tid = max(max_tid, T[i][j]);
        }
    }
    vector<vector<int>> P(50, vector<int>(50));
    for (int i = 0; i < 50; i++) {
        for (int j = 0; j < 50; j++) {
            cin >> P[i][j];
        }
    }
    vector<char> moves;
    int ci = si, cj = sj;
    vector<bool> used(max_tid + 1, false);
    used[T[si][sj]] = true;
    int dirs[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
    char dchar[4] = {'U', 'D', 'L', 'R'};
    while (true) {
        int best_val = -1;
        int best_count = -1;
        int best_d = -1;
        for (int d = 0; d < 4; d++) {
            int ni = ci + dirs[d][0];
            int nj = cj + dirs[d][1];
            if (ni >= 0 && ni < 50 && nj >= 0 && nj < 50) {
                int tid = T[ni][nj];
                if (!used[tid]) {
                    int max_onward = 0;
                    int count_onward = 0;
                    for (int dd = 0; dd < 4; dd++) {
                        int nni = ni + dirs[dd][0];
                        int nnj = nj + dirs[dd][1];
                        if (nni >= 0 && nni < 50 && nnj >= 0 && nnj < 50) {
                            int nt = T[nni][nnj];
                            if (nt != tid && !used[nt]) {
                                count_onward++;
                                max_onward = max(max_onward, P[nni][nnj]);
                            }
                        }
                    }
                    int this_val = P[ni][nj] + max_onward;
                    bool better = false;
                    if (this_val > best_val) {
                        better = true;
                    } else if (this_val == best_val && count_onward > best_count) {
                        better = true;
                    }
                    if (better) {
                        best_val = this_val;
                        best_count = count_onward;
                        best_d = d;
                    }
                }
            }
        }
        if (best_d == -1) break;
        int ni = ci + dirs[best_d][0];
        int nj = cj + dirs[best_d][1];
        ci = ni;
        cj = nj;
        used[T[ni][nj]] = true;
        moves.push_back(dchar[best_d]);
    }
    for (char c : moves) cout << c;
    cout << endl;
    return 0;
}