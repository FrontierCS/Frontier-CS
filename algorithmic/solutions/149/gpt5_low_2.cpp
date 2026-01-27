#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int k = 0; k < 1000; k++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) return 0;

        string path;
        int di = ti - si, dj = tj - sj;
        if (di < 0) path.append(-di, 'U');
        else path.append(di, 'D');
        if (dj < 0) path.append(-dj, 'L');
        else path.append(dj, 'R');

        cout << path << "\n" << flush;

        int feedback;
        if (!(cin >> feedback)) return 0;
    }
    return 0;
}