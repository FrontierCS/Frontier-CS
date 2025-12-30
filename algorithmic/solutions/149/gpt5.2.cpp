#include <bits/stdc++.h>
using namespace std;

static string manhattan_path(int si, int sj, int ti, int tj) {
    string p;
    if (ti > si) p.append(ti - si, 'D');
    else p.append(si - ti, 'U');
    if (tj > sj) p.append(tj - sj, 'R');
    else p.append(sj - tj, 'L');
    return p;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int a, b, c, d;
    if (!(cin >> a >> b >> c >> d)) return 0;

    // Interactive mode: first line is (si sj ti tj) in [0,29].
    if (0 <= a && a < 30 && 0 <= b && b < 30 && 0 <= c && c < 30 && 0 <= d && d < 30) {
        int si = a, sj = b, ti = c, tj = d;
        for (int k = 0; k < 1000; k++) {
            string p = manhattan_path(si, sj, ti, tj);
            cout << p << '\n' << flush;

            long long res;
            if (!(cin >> res)) break; // if judge ended unexpectedly

            if (!(cin >> si >> sj >> ti >> tj)) break;
        }
        return 0;
    }

    // Offline/local input mode: first comes all h and v, then queries.
    // We already read first 4 ints of h.
    constexpr int HN = 30 * 29;
    constexpr int VN = 29 * 30;

    int remainH = HN - 4;
    int tmp;
    for (int i = 0; i < remainH; i++) cin >> tmp;
    for (int i = 0; i < VN; i++) cin >> tmp;

    // Now process queries: each line contains at least 4 ints (si sj ti tj),
    // possibly followed by additional values (a_k e_k). Ignore the rest of the line.
    int si, sj, ti, tj;
    string rest;
    while (cin >> si >> sj >> ti >> tj) {
        getline(cin, rest);
        cout << manhattan_path(si, sj, ti, tj) << '\n';
    }
    return 0;
}