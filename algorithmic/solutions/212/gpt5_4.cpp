#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, L, R, Sx, Sy, Lq;
    long long s;
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) return 0;
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    auto isSubseq = [&](const vector<int>& order)->bool{
        int j = 0;
        for (int x : order) {
            if (j < Lq && q[j] == x) ++j;
        }
        return j == Lq;
    };

    auto generatePath = [&](const vector<int>& order, vector<pair<int,int>>& path)->bool{
        // detect if wrap exists (non-adjacent pair)
        // path generation with possible single wrap using available outside side(s)
        path.clear();
        bool hasLeft = (L > 1);
        bool hasRight = (R < m);

        auto sweepFrom = [&](int row, int startCol, vector<pair<int,int>>& path)->int{
            if (startCol == L) {
                for (int y = L + 1; y <= R; ++y) path.emplace_back(row, y);
                return R;
            } else {
                for (int y = R - 1; y >= L; --y) path.emplace_back(row, y);
                return L;
            }
        };

        int curRow = order[0];
        int curCol = L; // start at (Sx, L)
        path.emplace_back(curRow, curCol);
        curCol = sweepFrom(curRow, curCol, path);

        for (size_t i = 1; i < order.size(); ++i) {
            int nxtRow = order[i];
            if (abs(nxtRow - curRow) == 1) {
                // adjacent move inside stripe at current end
                path.emplace_back(nxtRow, curCol);
                curRow = nxtRow;
                curCol = sweepFrom(curRow, curCol, path);
            } else {
                // need to use outside at current end
                if (curCol == L) {
                    if (!hasLeft) return false;
                    int outY = L - 1;
                    path.emplace_back(curRow, outY);
                    int step = (nxtRow > curRow) ? 1 : -1;
                    while (curRow != nxtRow) {
                        curRow += step;
                        path.emplace_back(curRow, outY);
                    }
                    // step into stripe at L
                    path.emplace_back(curRow, L);
                    curCol = sweepFrom(curRow, L, path);
                } else { // curCol == R
                    if (!hasRight) return false;
                    int outY = R + 1;
                    path.emplace_back(curRow, outY);
                    int step = (nxtRow > curRow) ? 1 : -1;
                    while (curRow != nxtRow) {
                        curRow += step;
                        path.emplace_back(curRow, outY);
                    }
                    // step into stripe at R
                    path.emplace_back(curRow, R);
                    curCol = sweepFrom(curRow, R, path);
                }
            }
        }
        return true;
    };

    // Construct two candidate orders
    vector<int> orderA; // ascending circular: Sx..n, 1..Sx-1
    for (int i = Sx; i <= n; ++i) orderA.push_back(i);
    for (int i = 1; i < Sx; ++i) orderA.push_back(i);

    vector<int> orderB; // descending circular: Sx..1, n..Sx+1
    for (int i = Sx; i >= 1; --i) orderB.push_back(i);
    for (int i = n; i >= Sx + 1; --i) orderB.push_back(i);

    vector<pair<int,int>> bestPath, path;
    bool found = false;

    auto tryOrder = [&](const vector<int>& order)->bool{
        if (!isSubseq(order)) return false;
        vector<pair<int,int>> pth;
        if (!generatePath(order, pth)) return false;
        if (!found || pth.size() < bestPath.size()) {
            bestPath = move(pth);
            found = true;
        }
        return true;
    };

    tryOrder(orderA);
    tryOrder(orderB);

    if (!found) {
        cout << "NO\n";
        return 0;
    }

    cout << "YES\n";
    cout << bestPath.size() << "\n";
    for (auto &pt : bestPath) {
        cout << pt.first << " " << pt.second << "\n";
    }
    return 0;
}