#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<int> px(N), py(N), pt(N);
    for (int i = 0; i < N; i++) cin >> px[i] >> py[i] >> pt[i];
    int M;
    cin >> M;
    vector<int> hx(M), hy(M);
    for (int i = 0; i < M; i++) cin >> hx[i] >> hy[i];

    const int T = 300;
    for (int t = 0; t < T; t++) {
        string out(M, '.');
        cout << out << '\n' << flush;

        vector<string> petMoves(N);
        for (int i = 0; i < N; i++) {
            if (!(cin >> petMoves[i])) return 0;
        }
        // Update pet positions according to moves (not strictly necessary for this strategy)
        for (int i = 0; i < N; i++) {
            int x = px[i], y = py[i];
            const string& s = petMoves[i];
            if (s != ".") {
                for (char c : s) {
                    if (c == 'U') x--;
                    else if (c == 'D') x++;
                    else if (c == 'L') y--;
                    else if (c == 'R') y++;
                }
            }
            px[i] = x;
            py[i] = y;
        }
    }
    return 0;
}