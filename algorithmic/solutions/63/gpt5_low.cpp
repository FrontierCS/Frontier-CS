#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if(!(cin >> N >> M)) return 0;
    for(int i = 0; i < M; ++i){
        int u, v;
        cin >> u >> v;
    }

    // Placeholder non-interactive output: guess arbitrary distinct nodes.
    int A = 0, B = (N > 1 ? 1 : 0);
    if (A == B && N >= 2) B = 1;
    cout << 1 << " " << A << " " << B << "\n";
    cout.flush();
    return 0;
}