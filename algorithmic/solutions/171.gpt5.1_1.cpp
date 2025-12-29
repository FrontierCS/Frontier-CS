#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<int> I(M), J(M);
    for (int k = 0; k < M; ++k) {
        cin >> I[k] >> J[k];
    }

    int ci = I[0], cj = J[0];
    for (int k = 1; k < M; ++k) {
        int ti = I[k], tj = J[k];
        while (ci < ti) {
            cout << "M D\n";
            ++ci;
        }
        while (ci > ti) {
            cout << "M U\n";
            --ci;
        }
        while (cj < tj) {
            cout << "M R\n";
            ++cj;
        }
        while (cj > tj) {
            cout << "M L\n";
            --cj;
        }
    }

    return 0;
}