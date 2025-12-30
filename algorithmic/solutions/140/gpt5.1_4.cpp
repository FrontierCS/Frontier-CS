#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long b;
    int k, w;
    if (!(cin >> b >> k >> w)) return 0;

    auto ask = [&](long long sx, long long ty) -> long long {
        cout << "? 1 " << sx << " " << ty << '\n';
        cout.flush();
        long long d;
        if (!(cin >> d)) exit(0);
        return d;
    };

    if (k == 1 && w > 0) {
        long long Lx = -b, Rx = b;
        long long Ly = -b, Ry = b;
        int waves_used = 0;

        // Binary search for x using probes at (m,0) and (m+1,0)
        while (Lx < Rx && waves_used + 2 <= w) {
            long long mid = (Lx + Rx) / 2;
            long long d_mid = ask(mid, 0);
            waves_used++;
            if (waves_used >= w) break;
            long long d_mid1 = ask(mid + 1, 0);
            waves_used++;
            long long diff = d_mid1 - d_mid;
            if (diff > 0) {
                Rx = mid;
            } else {
                Lx = mid + 1;
            }
        }
        long long x_est = (Lx + Rx) / 2;

        // Binary search for y using probes at (0,m) and (0,m+1)
        while (Ly < Ry && waves_used + 2 <= w) {
            long long mid = (Ly + Ry) / 2;
            long long d_mid = ask(0, mid);
            waves_used++;
            if (waves_used >= w) break;
            long long d_mid1 = ask(0, mid + 1);
            waves_used++;
            long long diff = d_mid1 - d_mid;
            if (diff > 0) {
                Ry = mid;
            } else {
                Ly = mid + 1;
            }
        }
        long long y_est = (Ly + Ry) / 2;

        cout << "! " << x_est << " " << y_est << '\n';
        cout.flush();
    } else {
        cout << "!";
        for (int i = 0; i < k; ++i) {
            cout << " " << 0 << " " << 0;
        }
        cout << '\n';
        cout.flush();
    }

    return 0;
}