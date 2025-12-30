#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    while (true) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) break;

        string path;

        if (si < ti) path.append(ti - si, 'D');
        else path.append(si - ti, 'U');

        if (sj < tj) path.append(tj - sj, 'R');
        else path.append(sj - tj, 'L');

        cout << path << '\n';
        cout.flush();

        int res;
        if (!(cin >> res)) break;
    }

    return 0;
}