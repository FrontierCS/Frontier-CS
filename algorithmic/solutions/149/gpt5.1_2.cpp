#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int Q = 1000;
    for (int k = 0; k < Q; k++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) return 0;

        string path;
        if (ti > si) path.append(ti - si, 'D');
        else path.append(si - ti, 'U');
        if (tj > sj) path.append(tj - sj, 'R');
        else path.append(sj - tj, 'L');

        cout << path << '\n';
        cout.flush();

        long long feedback;
        if (!(cin >> feedback)) return 0;
    }

    return 0;
}