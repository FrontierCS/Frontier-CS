#include <bits/stdc++.h>

using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    int s = 0;
    long long ss = 0;
    do {
        s++;
        ss = 1LL * s * s * s;
    } while (ss < n);
    int cnt = 0;
    for(int i = 0; i < s && cnt < n; i++) {
        double px = (i + 0.5) / s;
        for(int j = 0; j < s && cnt < n; j++) {
            double py = (j + 0.5) / s;
            for(int k = 0; k < s && cnt < n; k++) {
                double pz = (k + 0.5) / s;
                printf("%.10f %.10f %.10f\n", px, py, pz);
                cnt++;
            }
        }
    }
    return 0;
}