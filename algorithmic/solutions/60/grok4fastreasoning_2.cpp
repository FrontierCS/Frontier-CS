#include <bits/stdc++.h>

using namespace std;

int main() {
    auto query_h = [](int y) -> double {
        cout << "query 0 " << y << " 100000 " << y << endl;
        double l;
        cin >> l;
        return l;
    };

    auto query_v = [](int x) -> double {
        cout << "query " << x << " 0 " << x << " 100000" << endl;
        double l;
        cin >> l;
        return l;
    };

    auto find_max_h = [&]() -> pair<int, double> {
        int low = 0, high = 100000;
        while (high - low >= 3) {
            int len = high - low;
            int m1 = low + len / 3;
            int m2 = low + 2 * len / 3;
            double v1 = query_h(m1);
            double v2 = query_h(m2);
            if (v1 < v2) {
                low = m1;
            } else {
                high = m2;
            }
        }
        double maxv = -1;
        int best = -1;
        for (int y = low; y <= high; ++y) {
            double v = query_h(y);
            if (v > maxv) {
                maxv = v;
                best = y;
            }
        }
        return {best, maxv};
    };

    auto find_max_v = [&]() -> pair<int, double> {
        int low = 0, high = 100000;
        while (high - low >= 3) {
            int len = high - low;
            int m1 = low + len / 3;
            int m2 = low + 2 * len / 3;
            double v1 = query_v(m1);
            double v2 = query_v(m2);
            if (v1 < v2) {
                low = m1;
            } else {
                high = m2;
            }
        }
        double maxv = -1;
        int best = -1;
        for (int x = low; x <= high; ++x) {
            double v = query_v(x);
            if (v > maxv) {
                maxv = v;
                best = x;
            }
        }
        return {best, maxv};
    };

    auto [cy, maxly] = find_max_h();
    long long r = round(maxly / 2.0);
    auto [cx, maxlx] = find_max_v();
    long long rx = round(maxlx / 2.0);
    cout << "answer " << cx << " " << cy << " " << r << endl;
    return 0;
}