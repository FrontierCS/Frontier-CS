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

    string actions(M, '.');
    for (int t = 0; t < 300; t++) {
        cout << actions << '\n';
        cout.flush();
    }
    return 0;
}