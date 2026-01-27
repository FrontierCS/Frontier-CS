#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    while (cin >> n >> m) {
        vector<int> mistakes(n, 0);
        int minMistakes = 0;
        double beta = 0.75;
        vector<double> powBeta(m + 1, 1.0);
        for (int i = 1; i <= m; ++i) powBeta[i] = powBeta[i - 1] * beta;

        for (int round = 0; round < m; ++round) {
            string s;
            if (!(cin >> s)) return 0;
            double sum0 = 0.0, sum1 = 0.0;
            for (int i = 0; i < n; ++i) {
                int dif = mistakes[i] - minMistakes;
                double w = powBeta[dif];
                if (s[i] == '1') sum1 += w;
                else sum0 += w;
            }
            char pred = (sum1 > sum0) ? '1' : '0';
            cout << pred << '\n';
            cout.flush();

            string actualStr;
            if (!(cin >> actualStr)) return 0;
            char actual = actualStr[0];

            int newMin = INT_MAX;
            for (int i = 0; i < n; ++i) {
                if (s[i] != actual) ++mistakes[i];
                if (mistakes[i] < newMin) newMin = mistakes[i];
            }
            minMistakes = newMin;
        }
    }
    return 0;
}