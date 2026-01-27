#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int q = 0; q < 1000; q++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) break;

        string path;
        int di = ti - si;
        int dj = tj - sj;

        // Simple Manhattan path: horizontal moves then vertical moves
        if (dj < 0) path.append(-dj, 'L');
        else path.append(dj, 'R');

        if (di < 0) path.append(-di, 'U');
        else path.append(di, 'D');

        cout << path << "\n" << flush;

        long long feedback;
        if (!(cin >> feedback)) break;
    }

    return 0;
}