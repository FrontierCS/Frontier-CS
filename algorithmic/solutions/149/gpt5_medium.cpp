#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int k = 0; k < 1000; k++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) return 0;

        string path;
        if (ti < si) path.append(si - ti, 'U');
        else path.append(ti - si, 'D');
        if (tj < sj) path.append(sj - tj, 'L');
        else path.append(tj - sj, 'R');

        cout << path << '\n' << flush;

        int result;
        if (!(cin >> result)) break;
    }
    return 0;
}