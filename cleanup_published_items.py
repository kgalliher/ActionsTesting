from typing import Optional
from arcgis.gis import GIS
from datetime import datetime, timedelta

from arcgis.gis._impl._content_manager import RecycleBin


def delete_all_from_recycle_bin(gis: GIS, tag: Optional[str] = None):
    """
    Delete all items from the AGOL org's Recycle Bin.
    :param gis: GIS: The GIS
    :param tag: str: Optional tag to narrow search
    :return: void
    """
    count = 0
    recycle_bin = RecycleBin(gis=gis)
    if tag:
        contents = [i for i in recycle_bin.content if tag in i.properties["tags"]]
    else:
        contents = recycle_bin.content
    print(f"Deleting items from the recycle bin...")
    try:
        for content in contents:
            print(f"\tDeleting {content.properties['title']}")
            # content.delete()
            count += 1
        print("Delete", count, "items from the recycle bin")
        # Report what was deleted
        #
    except Exception as ex:
        # If
        print(ex)


def delete_all_items(
    gis: GIS,
    username: str = "arcgis_python",
    tags: str = None,
    search_str: str = None,
    day_difference: int = 90,
):
    """
    Get all portal items owned by a specific user and delete them if they are not delete protected and older than a specified number of days.
    :param gis: GIS: The GIS
    :param username: str: The name of the user whose items should be deleted: Default is arcgis_python
    :param tags: str: An optional comma separated string of tags to limit the search
    :param search_str: str: An option search string e.g. `title:my_tile` or `type:CSV`
    :param day_difference: int: Difference in days from current date. Default is 90
    :return: void
    """
    timestamp_previous_year = (
        datetime.now() - timedelta(days=day_difference)
    ).timestamp() * 1000

    query = f"owner:{username}"
    if tags:
        query = f"owner:{username} AND tags:{tags}"
    if search_str:
        query = f"owner:{username} AND {search_str}"
    if tags and search_str:
        query = f"owner:{username} AND tags: {tags} AND {search_str}"
    all_items = gis.content.search(
        query=query,
        max_items=10000,
        sort_field="created",
        sort_order="asc",
    )
    item_count = 0
    for item in all_items:
        if item.modified < timestamp_previous_year:
            if item.can_delete:
                print(f"Deleting {item.title}")
                try:
                    source_item = item.related_items("Service2Data", "forward")[0]
                    if source_item:
                        print(f"\tDeleted source item: {item.title}")
                        item_count += 1
                        print(f"\tDeleted child item: {item.title}")
                        item_count += 1
                        source_item.delete(permanent=True)
                        item.delete(permanent=True)
                except IndexError:
                    try:
                        item.delete(permanent=True)
                        print(f"\tDeleted item: {item.title}")
                        item_count += 1
                    except Exception as ex:
                        if "Unable to delete item" in str(
                            ex
                        ) and "(Error Code: 500)" in str(ex):
                            pass
                        print(ex)
                except Exception as ex:
                    pass
                    print(f"\tFailed to delete item: {item} -> {str(ex)}")
    print(f"Deleted {item_count} items from {gis.url}")


if __name__ == "__main__":
    gis_agol = GIS(
        url="https://geosaurus.maps.arcgis.com/",
        username="arcgis_python",
        password="amazing_arcgis_123",
    )
    gis_ent = GIS(
        url="https://pythonapitestnb.dev.geocloud.com/portal",
        username="arcgis_python",
        password="amazing_arcgis_123",
        verify_cert=False,
    )

    delete_all_items(gis_agol, tags="integration", day_difference=0)
    delete_all_from_recycle_bin(gis_agol, "ntgrtn-tst")
    delete_all_items(
        gis_ent,
        tags="integration",
        day_difference=0,
    )
