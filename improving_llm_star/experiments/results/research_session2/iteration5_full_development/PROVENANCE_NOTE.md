The full-development process imported its modules before optional frontier/scheduling
experiments were added to the working tree. The old harness hashed files at the
end of a run, so its efficient.py hash describes that later on-disk version rather
than the exact imported version. Evaluated modes used the earlier implementation;
new options did not exist in that process. Treat this as exploratory evidence, not
a release-source reproduction artifact. The next harness versions snapshot all
sources at run start and final selected/validation/fresh evaluations will use
frozen committed sources. Historical result bytes are preserved unchanged.
