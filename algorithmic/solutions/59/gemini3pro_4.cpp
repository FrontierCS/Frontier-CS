#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <numeric>

using namespace std;

// Function to perform query
char query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    char res;
    cin >> res;
    return res;
}

struct Bucket {
    vector<int> elements;
    int hole_count = 0;
};

int main() {
    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "! 1" << endl;
        return 0;
    }

    vector<Bucket> buckets;
    vector<int> pivots; // pivots[i] is between buckets[i] and buckets[i+1]

    // Initial state: one bucket with 2 holes
    buckets.push_back(Bucket());
    buckets[0].hole_count = 2;

    for (int i = 1; i <= n; ++i) {
        // Find indices of first two buckets with holes
        int b1 = -1, b2 = -1;
        for (int k = 0; k < buckets.size(); ++k) {
            if (buckets[k].hole_count > 0) {
                if (b1 == -1) b1 = k;
                else {
                    b2 = k;
                    break;
                }
            }
        }
        // If only one bucket has holes (it must have 2, or 1 if n is end case, but holes sum to 2 usually)
        if (b2 == -1) b2 = b1;

        int chosen_bucket = -1;
        bool is_new = false;

        if (b1 == b2) {
            // Holes are in the same bucket
            // Check if i < pivot after b1
            if (b1 < pivots.size()) {
                char res = query(i, pivots[b1]);
                if (res == '<') {
                    chosen_bucket = b1;
                } else {
                    is_new = true;
                }
            } else {
                // No pivot after b1, so it's the last bucket
                // New candidate is also effectively in this bucket (or after).
                // But New is definitely larger than holes.
                // Since we can't compare with non-existent pivot, and New is the only thing > holes,
                // we treat "New" as simply adding to the last bucket?
                // Wait, if we pick New, it becomes a Pivot.
                // If we pick Hole, it goes to bucket.
                // If we have no pivot to compare, we have ambiguity?
                // No, "New" is always i+2. Holes are < i+2.
                // If we are at the end, we can't distinguish Hole from New by value comparison with Pivot.
                // But we know Hole < New.
                // We can just add to the bucket. If it's New, it will be largest.
                // If it's Hole, smaller.
                // We can resolve by sorting bucket later.
                // So if b1 is last bucket, just put in b1.
                // BUT, we must correctly maintain hole counts.
                // If we put in b1, do we consume a hole or is it New?
                // This is the tricky case.
                // However, "New" creates a pivot only if we can distinguish it.
                // If we cannot distinguish, we just dump into bucket.
                // We assume it's a hole? If we decrement hole count, but it was New...
                // Actually, if b1 is last, we just add to b1.
                // We treat it as consuming a hole?
                // If we treat it as consuming a hole, we add a hole to "new last"?
                // If b1 was last, "new last" is b1.
                // So hole count -1 +1 = 0 change.
                // If it was New, we effectively increased holes count by 1 (New added) and filled one spot.
                // So count is consistent.
                chosen_bucket = b1;
            }
        } else {
            // Holes in different buckets b1 < b2
            // Compare with pivot before b2 (which is pivots[b2-1])
            char res = query(i, pivots[b2 - 1]);
            if (res == '<') { // i < P_{b2-1}
                chosen_bucket = b1;
            } else { // i > P_{b2-1}
                // in b2 or New
                if (b2 < pivots.size()) {
                    char res2 = query(i, pivots[b2]);
                    if (res2 == '<') {
                        chosen_bucket = b2;
                    } else {
                        is_new = true;
                    }
                } else {
                    // b2 is last. Can't distinguish b2 hole vs New.
                    // Put in b2.
                    chosen_bucket = b2;
                }
            }
        }

        if (is_new) {
            // i is New (i+2). Becomes pivot.
            pivots.push_back(i);
            buckets.push_back(Bucket());
            // Hole counts don't change locations, but New is not a hole.
            // No hole consumed.
        } else {
            // i is in chosen_bucket
            buckets[chosen_bucket].elements.push_back(i);
            buckets[chosen_bucket].hole_count--;
            // Add a hole to the last bucket
            buckets.back().hole_count++;
        }
    }

    // Now sort each bucket
    vector<int> result(n + 1);
    int current_val = 1;
    for (int k = 0; k < buckets.size(); ++k) {
        // Sort buckets[k].elements
        // Use std::sort with custom comparator
        sort(buckets[k].elements.begin(), buckets[k].elements.end(), [&](int a, int b) {
            char res = query(a, b);
            return res == '<';
        });

        for (int idx : buckets[k].elements) {
            result[idx] = current_val++;
        }
        if (k < pivots.size()) {
            result[pivots[k]] = current_val++;
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << result[i];
    }
    cout << endl;

    return 0;
}