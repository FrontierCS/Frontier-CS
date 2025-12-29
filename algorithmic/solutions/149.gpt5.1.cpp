#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int q = 0; q < 1000; ++q) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) return 0;

        string path;
        if (si < ti) path.append(ti - si, 'D');
        else path.append(si - ti, 'U');
        if (sj < tj) path.append(tj - sj, 'R');
        else path.append(sj - tj, 'L');

        cout << path << '\n' << flush;

        long long res;
        if (!(cin >> res)) return 0;
        if (res < 0) return 0;
    }
    return 0;
}