#include <bits/stdc++.h>
using namespace std;
using ll = long long;

struct Rect {
    ll x1, x2, y1, y2;
    __int128 area() const {
        return (__int128)(x2 - x1 + 1) * (y2 - y1 + 1);
    }
    bool operator<(const Rect& other) const {
        return area() < other.area();
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    ll n;
    cin >> n;

    priority_queue<Rect> pq;
    pq.push({1, n, 1, n});

    while (true) {
        Rect r = pq.top();
        pq.pop();

        if (r.x1 == r.x2 && r.y1 == r.y2) {
            cout << r.x1 << " " << r.y1 << endl;
            cout.flush();
            int res;
            cin >> res;
            // should be 0
            break;
        }

        ll x = (r.x1 + r.x2) / 2;
        ll y = (r.y1 + r.y2) / 2;

        cout << x << " " << y << endl;
        cout.flush();

        int res;
        cin >> res;

        if (res == 0) {
            break;
        } else if (res == 1) {
            ll nx1 = max(r.x1, x + 1);
            if (nx1 <= r.x2) {
                pq.push({nx1, r.x2, r.y1, r.y2});
            }
        } else if (res == 2) {
            ll ny1 = max(r.y1, y + 1);
            if (ny1 <= r.y2) {
                pq.push({r.x1, r.x2, ny1, r.y2});
            }
        } else { // res == 3
            if (r.y1 <= y - 1) {
                pq.push({r.x1, r.x2, r.y1, y - 1});
            }
            if (r.x1 <= x - 1) {
                pq.push({r.x1, x - 1, y, r.y2});
            }
        }
    }

    return 0;
}