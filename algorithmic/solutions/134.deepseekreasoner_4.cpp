#include <iostream>
#include <queue>
#include <vector>
using namespace std;

struct Rect {
    long long la, ra, lb, rb;
    long double area() const {
        return (long double)(ra - la + 1) * (rb - lb + 1);
    }
};

struct CompareRect {
    bool operator()(const Rect& a, const Rect& b) {
        return a.area() < b.area();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    long long n;
    cin >> n;

    priority_queue<Rect, vector<Rect>, CompareRect> pq;
    pq.push({1, n, 1, n});

    int queries = 0;
    while (queries < 10000) {
        Rect rect = pq.top();
        pq.pop();

        if (rect.la == rect.ra && rect.lb == rect.rb) {
            cout << rect.la << " " << rect.lb << endl;
            cout.flush();
            queries++;
            int response;
            cin >> response;
            if (response == 0) break;
            continue;
        }

        long long mx = rect.la + (rect.ra - rect.la) / 2;
        long long my = rect.lb + (rect.rb - rect.lb) / 2;

        cout << mx << " " << my << endl;
        cout.flush();
        queries++;
        int response;
        cin >> response;

        if (response == 0) {
            break;
        } else if (response == 1) {
            if (mx + 1 <= rect.ra) {
                pq.push({mx + 1, rect.ra, rect.lb, rect.rb});
            }
        } else if (response == 2) {
            if (my + 1 <= rect.rb) {
                pq.push({rect.la, rect.ra, my + 1, rect.rb});
            }
        } else if (response == 3) {
            if (mx - 1 >= rect.la) {
                pq.push({rect.la, mx - 1, rect.lb, rect.rb});
            }
            if (my - 1 >= rect.lb) {
                pq.push({mx, rect.ra, rect.lb, my - 1});
            }
        }
    }

    return 0;
}