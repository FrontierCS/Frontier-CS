#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, L;
    cin >> N >> L;
    vector<int> T(N);
    for (int i = 0; i < N; i++) {
        cin >> T[i];
    }
    for (int i = 0; i < N; i++) {
        int ai = i;
        int bi = (i + 1) % N;
        cout << ai << " " << bi << '\n';
    }
    return 0;
}