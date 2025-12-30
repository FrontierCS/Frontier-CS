#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int Q = 1000;
    for (int k = 0; k < Q; ++k) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) return 0;

        string path;
        int di = ti - si;
        if (di > 0) path.append(di, 'D');
        else if (di < 0) path.append(-di, 'U');

        int dj = tj - sj;
        if (dj > 0) path.append(dj, 'R');
        else if (dj < 0) path.append(-dj, 'L');

        cout << path << '\n';
        cout.flush();

        int feedback;
        if (!(cin >> feedback)) return 0;
    }
    return 0;
}