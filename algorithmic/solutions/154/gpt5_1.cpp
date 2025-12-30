#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<int> px(N), py(N), pt(N);
    for (int i = 0; i < N; i++) {
        cin >> px[i] >> py[i] >> pt[i];
    }
    int M;
    cin >> M;
    vector<int> hx(M), hy(M);
    for (int i = 0; i < M; i++) cin >> hx[i] >> hy[i];

    for (int turn = 0; turn < 300; turn++) {
        string actions(M, '.');
        cout << actions << '\n' << flush;

        for (int i = 0; i < N; i++) {
            string s;
            if (!(cin >> s)) return 0;
        }
    }
    return 0;
}