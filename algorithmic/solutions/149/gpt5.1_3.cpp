#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int k = 0; k < 1000; k++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) return 0;

        string path;
        int dy = tj - sj;
        if (dy > 0) path.append(dy, 'R');
        else path.append(-dy, 'L');

        int dx = ti - si;
        if (dx > 0) path.append(dx, 'D');
        else path.append(-dx, 'U');

        cout << path << endl;
        cout.flush();

        int res;
        if (!(cin >> res)) return 0;
    }

    return 0;
}