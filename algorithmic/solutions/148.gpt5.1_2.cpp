#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 50;
    int si, sj;
    if (!(cin >> si >> sj)) return 0;

    static int t[N][N];
    static int pval[N][N];
    int maxID = -1;

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> t[i][j];
            if (t[i][j] > maxID) maxID = t[i][j];
        }
    }
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> pval[i][j];
        }
    }

    vector<char> visitedTile(maxID + 1, 0);
    int curi = si, curj = sj;
    visitedTile[t[curi][curj]] = 1;

    string res;
    int di[4] = {-1, 1, 0, 0};
    int dj[4] = {0, 0, -1, 1};
    char dc[4] = {'U', 'D', 'L', 'R'};

    while (true) {
        int bestVal = -1;
        int bestk = -1;
        int besti = -1, bestj = -1;

        for (int k = 0; k < 4; k++) {
            int ni = curi + di[k];
            int nj = curj + dj[k];
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            int id = t[ni][nj];
            if (visitedTile[id]) continue;
            int val = pval[ni][nj];
            if (val > bestVal) {
                bestVal = val;
                bestk = k;
                besti = ni;
                bestj = nj;
            }
        }

        if (bestk == -1) break;

        res.push_back(dc[bestk]);
        curi = besti;
        curj = bestj;
        visitedTile[t[curi][curj]] = 1;
    }

    cout << res << '\n';
    return 0;
}